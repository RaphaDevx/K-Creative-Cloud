"""Small exec helper that gives a new process session a controlling PTY."""
import fcntl
import os
import sys
import termios


def run(argv):
    if not argv:
        raise ValueError('PTY executable required')
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    os.execvpe(argv[0], argv, os.environ)


if __name__ == '__main__':
    run(sys.argv[1:])
