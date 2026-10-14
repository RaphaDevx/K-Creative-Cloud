#!/usr/bin/env python3
"""Linux screen recording, a real Calc demo, MP4 exports and local upload package."""
import argparse
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import tempfile
import time
import uuid


def run(args):
    result=subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))


def fresh(path):
    path=Path(path).resolve()
    if path.exists():raise ValueError(f'Output already exists: {path}')
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


def stop(proc):
    if proc and proc.poll() is None:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait()


def recorder(display,width,height,seconds,output):
    if not re.fullmatch(r':\d+(?:\.\d+)?(?:\+\d+,\d+)?',display):raise ValueError('Expected local X11 display, e.g. :0.0')
    return subprocess.Popen(['ffmpeg','-nostdin','-n','-loglevel','error','-f','x11grab','-draw_mouse','1','-framerate','15','-video_size',f'{width}x{height}','-i',display,'-t',str(seconds),'-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],start_new_session=True)


def record(args):
    out=fresh(args.output)
    proc=recorder(args.display,args.width,args.height,args.seconds,out)
    try:
        if proc.wait(timeout=args.seconds+15):raise RuntimeError('Screen recorder failed')
    finally:stop(proc)
    return {'raw_video':str(out),'duration':probe(out)['format']['duration']}


def demo(args):
    import uno
    folder=Path(args.output_dir).resolve()
    if folder.exists():raise ValueError('Use a new output directory')
    folder.mkdir(parents=True)
    xvfb=office=video=None
    with tempfile.TemporaryDirectory(prefix='kai-calc-') as work:
        rd,wr=os.pipe()
        try:
            xvfb=subprocess.Popen(['Xvfb','-displayfd',str(wr),'-screen','0','1280x720x24','-nolisten','tcp'],pass_fds=(wr,),start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            os.close(wr);wr=None
            if not select.select([rd],[],[],10)[0]:raise RuntimeError('Xvfb startup timed out')
            display=':'+os.read(rd,64).decode().strip()
            pipe='kai_'+uuid.uuid4().hex
            office=subprocess.Popen(['libreoffice',f'-env:UserInstallation={Path(work).as_uri()}/profile','--nologo','--nodefault','--norestore','--nofirststartwizard',f'--accept=pipe,name={pipe};urp;StarOffice.ServiceManager'],env=dict(os.environ,DISPLAY=display),start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            resolver=uno.getComponentContext().ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',uno.getComponentContext())
            context=None
            for _ in range(60):
                try:context=resolver.resolve(f'uno:pipe,name={pipe};urp;StarOffice.ComponentContext');break
                except Exception:
                    if office.poll() is not None:raise RuntimeError('LibreOffice startup failed')
                    time.sleep(.3)
            if context is None:raise RuntimeError('UNO connection timed out')
            desktop=context.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',context)
            doc=desktop.loadComponentFromURL('private:factory/scalc','_blank',0,())
            sheet=doc.Sheets.getByIndex(0);sheet.Name='Loesung'
            doc.CurrentController.ZoomValue=160
            sheet.Columns.getByIndex(0).Width=6000;sheet.Columns.getByIndex(1).Width=7000
            sheet.getCellRangeByName('A1:B6').CharHeight=18
            sheet.getCellRangeByName('A1:B1').CharWeight=150
            time.sleep(2)
            raw=folder/'capture.mp4';video=recorder(display,1280,720,18,raw)
            time.sleep(1)
            sheet.getCellRangeByName('A1').String='Werte';time.sleep(2)
            for cell,value in [('A2',10),('A3',20),('A4',30)]:
                doc.CurrentController.select(sheet.getCellRangeByName(cell));sheet.getCellRangeByName(cell).Value=value;time.sleep(2)
            sheet.getCellRangeByName('B1').String='Mittelwert'
            sheet.getCellRangeByName('B2').Formula='=SUM(A2:A4)/COUNT(A2:A4)'
            doc.CurrentController.select(sheet.getCellRangeByName('B2'))
            assert sheet.getCellRangeByName('B2').Value==20
            prop=uno.createUnoStruct('com.sun.star.beans.PropertyValue');prop.Name='FilterName';prop.Value='Calc MS Excel 2007 XML'
            doc.storeAsURL((folder/'solution.xlsx').as_uri(),(prop,))
            if video.wait(timeout=25):raise RuntimeError('Recording failed')
            (folder/'steps.srt').write_text('1\n00:00:01,000 --> 00:00:03,000\nWerte in Spalte A eintragen.\n\n2\n00:00:03,000 --> 00:00:09,000\nDie drei Werte sind 10, 20 und 30.\n\n3\n00:00:09,000 --> 00:00:18,000\nSumme / Anzahl = Mittelwert 20.\n',encoding='utf-8')
            result={'application':'LibreOffice Calc','not_excel':True,'formula':'=SUM(A2:A4)/COUNT(A2:A4)','verified_value':20,'raw_video':str(raw),'workbook':str(folder/'solution.xlsx')}
            (folder/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
            doc.close(True)
            return result
        finally:
            if wr is not None:os.close(wr)
            os.close(rd)
            for proc in (video,office,xvfb):stop(proc)


def export(args):
    source=args.input.resolve();out=fresh(args.output)
    if not source.is_file():raise ValueError('Input video not found')
    if out.suffix.lower()!='.mp4':raise ValueError('Output must have .mp4 extension')
    # Padding keeps all cells visible; no automatic vertical crop.
    size=(1920,1080) if args.format=='landscape' else (1080,1920)
    w,h=size
    filters=f'scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1'
    command=['ffmpeg','-nostdin','-n','-loglevel','error','-i',str(source)]
    if args.audio:
        command+=['-i',str(args.audio.resolve()),'-map','0:v:0','-map','1:a:0','-shortest']
    else:command+=['-map','0:v:0','-map','0:a?']
    command+=['-vf',filters,'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(out)]
    with tempfile.TemporaryDirectory(prefix='kai-captions-') as work:
        if args.captions:
            captions=Path(work)/'captions.srt';shutil.copyfile(args.captions,captions)
            index=command.index('-vf')+1
            command[index]+=f",subtitles=filename='{captions}'"
        run(command)
    return {'video':str(out),'format':args.format,'media':probe(out)}


def package(args):
    source=args.input.resolve();media=probe(source)
    stream=next(s for s in media['streams'] if s['codec_type']=='video')
    if source.suffix.lower()!='.mp4':raise ValueError('Package requires an MP4 export')
    if stream['codec_name']!='h264' or stream.get('pix_fmt')!='yuv420p':raise ValueError('Export H.264/yuv420p MP4 first')
    folder=Path(args.output_dir).resolve()
    if folder.exists():raise ValueError('Package directory already exists')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',args.slug):raise ValueError('Unsafe slug')
    folder.mkdir(parents=True)
    filename=args.slug+'.mp4';shutil.copyfile(source,folder/filename)
    run(['ffmpeg','-nostdin','-n','-loglevel','error','-ss',str(min(1,float(media['format']['duration'])/2)),'-i',str(source),'-frames:v','1',str(folder/'thumbnail.jpg')])
    seconds=float(media['format']['duration'])
    entry={'id':args.slug,'type':'localvideo','course':args.course,'title':args.title,'subtitle':'Bildschirm-Tutorial','description':args.description,'topics':args.topic,'duration':f'{int(seconds)//60}:{int(seconds)%60:02d}','video_src':None,'thumbnail_emoji':'📊','block':args.block}
    (folder/'feed-entry.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
    (folder/'upload-plan.json').write_text(json.dumps({'status':'local_ready_not_uploaded','file':filename,'bytes':source.stat().st_size,'dimensions':[stream['width'],stream['height']],'course':args.course,'slug':args.slug,'needs':['verify current course id and storage backend','upload MP4 and verify URL','set video_src','register in videos catalog and unauthenticated feed fallback as applicable']},indent=2)+'\n')
    return {'package':str(folder),'status':'local_ready_not_uploaded'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('demo-calc');p.add_argument('--output-dir',required=True);p.set_defaults(fn=demo)
    p=sub.add_parser('record');p.add_argument('--display',required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=720);p.add_argument('--output',type=Path,required=True);p.set_defaults(fn=record)
    p=sub.add_parser('export');p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--format',choices=['landscape','portrait'],default='landscape');p.add_argument('--audio',type=Path);p.add_argument('--captions',type=Path,help='SRT to burn into export');p.set_defaults(fn=export)
    p=sub.add_parser('package');p.add_argument('--input',type=Path,required=True);p.add_argument('--output-dir',required=True);p.add_argument('--slug',required=True);p.add_argument('--course',required=True);p.add_argument('--title',required=True);p.add_argument('--description',default='');p.add_argument('--topic',action='append',default=[]);p.add_argument('--block',default='');p.set_defaults(fn=package)
    args=parser.parse_args()
    if args.cmd=='record' and (not 1<=args.seconds<=3600 or not 2<=args.width<=7680 or not 2<=args.height<=4320):parser.error('Invalid duration/dimensions')
    try:print(json.dumps(args.fn(args),ensure_ascii=False))
    except (ValueError,RuntimeError,subprocess.SubprocessError) as e:parser.exit(1,f'{e}\n')

if __name__=='__main__':main()
