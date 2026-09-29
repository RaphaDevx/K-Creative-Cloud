"""
DJ Set Tracklist — 6h+ Set
Organisiert in Vibe-Phasen, optimiert für YouTube-Suche.
Jeder Track hat: (artist, title, search_hint)
search_hint = präzisere Suchphrase wenn Remix/Edit spezifisch
"""

PHASES = {

    "1_WARMUP_INDIE_POP": {
        "label": "Warmup — Indie, Sleaze & Pop Trash (120–126 BPM)",
        "tracks": [
            ("Empire of the Sun",   "We Are The People",            None),
            ("Empire of the Sun",   "Walking On A Dream",           None),
            ("MGMT",                "Kids",                         None),
            ("The Ting Tings",      "That's Not My Name",           None),
            ("Kelis",               "Trick Me",                     None),
            ("Gwen Stefani",        "Hollaback Girl",               None),
            ("Nelly Furtado",       "Promiscuous",                  None),
            ("Nelly Furtado",       "Maneater",                     None),
            ("Rihanna",             "Only Girl In The World",       "Rihanna Only Girl In The World extended club mix"),
            ("Lady Gaga",           "Poker Face",                   None),
            ("Britney Spears",      "Toxic",                        None),
            ("Madonna",             "Hung Up",                      None),
            ("ABBA",                "Gimme Gimme Gimme",            "ABBA Gimme Gimme Gimme Sgt Slick edit"),
            ("Black Eyed Peas",     "Pump It",                      None),
            ("The Prodigy",         "Omen",                         None),
            ("David Guetta",        "Sexy Bitch",                   None),
            ("Icona Pop",           "I Love It",                    None),
            ("Calvin Harris",       "Summer",                       None),
            ("Rihanna Calvin Harris","We Found Love",               None),
            ("Lady Gaga",           "Bad Romance",                  None),
        ]
    },

    "2_LATIN_REGGAETON": {
        "label": "Latin Tech, Reggaeton & Afro Groove (124–130 BPM)",
        "tracks": [
            ("FloyyMenor Cris Mj",  "Gata Only",                    None),
            ("AEREA",               "Chingona",                     "La Santa AEREA Chingona"),
            ("AEREA",               "Kintsugi",                     None),
            ("AEREA",               "Kassandra",                    None),
            ("AEREA",               "Esta Noche",                   None),
            ("Hugel Topic",         "I Adore You",                  "Hugel Topic Arash I Adore You"),
            ("Hugel Mercadone",     "Marianela Que Pasa",           None),
            ("Pitbull Ne-Yo Afrojack","Give Me Everything",         None),
            ("Jennifer Lopez Pitbull","On The Floor",               None),
            ("Pitbull",             "Hotel Room Service",           None),
            ("Pitbull",             "Fireball",                     None),
            ("Don Omar",            "Danza Kuduro",                 None),
            ("Daddy Yankee",        "Gasolina",                     None),
            ("Farruko",             "Pepas",                        None),
            ("J Balvin Willy William","Mi Gente",                   None),
            ("Bad Bunny",           "Tití Me Preguntó",             None),
            ("Rauw Alejandro",      "Todo De Ti",                   None),
            ("Pitbull Kesha",       "Timber",                       None),
            ("Cloonee",             "Stephanie",                    None),
            ("Cloonee",             "Si Sip",                       None),
            ("San Pacho",           "Amor",                         None),
            ("ACRAZE",              "Do It To It",                  None),
            ("Fisher",              "Losing It",                    None),
        ]
    },

    "3_FRENCH_TOUCH_GROOVE": {
        "label": "French Touch, Electroclash & Decadence (126–128 BPM)",
        "tracks": [
            ("Discobitch",          "C'est beau la bourgeoisie",    None),
            ("Helmut Fritz",        "Ça m'énerve",                  None),
            ("Miss Kittin The Hacker","Frank Sinatra",              None),
            ("Miss Kittin The Hacker","1982",                       None),
            ("Yelle",               "A Cause Des Garçons",          "Yelle A Cause Des Garcons Tck Tck Tck Remix"),
            ("Stromae",             "Alors On Danse",               None),
            ("Benny Benassi",       "Satisfaction",                 None),
            ("Justice Simian",      "We Are Your Friends",          None),
            ("Daft Punk",           "One More Time",                None),
            ("Kavinsky",            "Nightcall",                    None),
            ("Modjo",               "Lady Hear Me Tonight",         None),
            ("Duck Sauce",          "Barbra Streisand",             None),
            ("Mau P",               "Drugs From Amsterdam",         None),
            ("Dom Dolla",           "Rhyme Dust",                   None),
        ]
    },

    "4_ABRISS_MITSING": {
        "label": "Abriss & Mitsing-Hymnen — Peak Party (128–132 BPM)",
        "tracks": [
            ("Cascada",             "Everytime We Touch",           None),
            ("Cascada",             "Evacuate the Dancefloor",      None),
            ("Haddaway",            "What Is Love",                 None),
            ("Gigi D'Agostino",     "L'Amour Toujours",             None),
            ("Vengaboys",           "Boom Boom Boom Boom",          None),
            ("Peter Fox",           "Alles Neu",                    None),
            ("Deichkind",           "Remmidemmi",                   None),
            ("Seeed",               "Ding",                         None),
            ("Scooter",             "Maria I Like It Loud",         None),
            ("Guru Josh Project",   "Infinity 2008",                "Guru Josh Project Infinity 2008 Klaas Remix"),
            ("Avicii",              "Levels",                       None),
            ("Avicii",              "Wake Me Up",                   None),
            ("LMFAO",               "Party Rock Anthem",            None),
            ("Taio Cruz",           "Dynamite",                     None),
            ("Swedish House Mafia", "Don't You Worry Child",        None),
            ("Macklemore Ryan Lewis","Can't Hold Us",               None),
            ("The Killers",         "Mr. Brightside",               None),
            ("Sweet Caroline",      "Neil Diamond",                 "Neil Diamond Sweet Caroline"),
            ("Bon Jovi",            "Livin on a Prayer",            None),
            ("David Guetta Sia",    "Titanium",                     None),
            ("Flo Rida",            "Club Can't Handle Me",         None),
        ]
    },

    "5_90s_RAVE_CLASSICS": {
        "label": "90s/2000s Rave Classics & Anthems (128–135 BPM)",
        "tracks": [
            ("U96",                 "Club Bizarre",                 None),
            ("Faithless",           "Insomnia",                     "Faithless Insomnia Monster Mix"),
            ("Robert Miles",        "Children Dream Version",       None),
            ("Gala",                "Freed From Desire",            None),
            ("Darude",              "Sandstorm",                    None),
            ("Alice Deejay",        "Better Off Alone",             None),
            ("Zombie Nation",       "Kernkraft 400",                None),
            ("ATB",                 "9 PM Till I Come",             None),
            ("Groove Coverage",     "God Is A Girl",                None),
            ("The Chemical Brothers","Hey Boy Hey Girl",            None),
            ("Energy 52",           "Cafe Del Mar",                 None),
            ("Delerium Sarah McLachlan","Silence",                  "Delerium Silence Tiesto Remix"),
            ("Bicep",               "Glue",                         None),
            ("Fred again Swedish House Mafia","Turn On The Lights again",None),
            ("John Summit",         "Where You Are",                None),
        ]
    },

    "6_TECHNO_BOOTLEGS": {
        "label": "Pop Gone Techno — Bootlegs & Remixes (135–145 BPM)",
        "tracks": [
            ("U96",                 "Club Bizarre Techno Remix",    "Club Bizarre LAUWEND Techno Remix"),
            ("Peggy Gou",           "Nanana",                       "Peggy Gou It Goes Like Nanana"),
            ("Lady Gaga",           "Poker Face Hard Techno",       "Lady Gaga Poker Face Klangkuenstler bootleg"),
            ("Rihanna",             "Only Girl Hard Techno Edit",   "Rihanna Only Girl Hard Techno edit"),
            ("Faithless",           "Insomnia 2021",                "Faithless Insomnia Maceo Plex 2021"),
            ("Robert Miles",        "Children Tinlicker Remix",     None),
            ("Haddaway",            "What Is Love Techno",          "Haddaway What Is Love techno bootleg"),
            ("Kylie Minogue",       "Can't Get You Out Of My Head Remix", "Kylie Minogue Can't Get You Out Of My Head Peggy Gou"),
            ("Kid Cudi",            "Day N Night Techno",           "Kid Cudi Day N Night hard techno edit"),
            ("Mau P",               "Club Bizarre",                 None),
            ("Eli Brown",           "Believe",                      None),
            ("Nelly Furtado",       "Maneater Techno",              "Nelly Furtado Maneater techno remix"),
        ]
    },

    "7_FAST_TRANCE_EURODANCE": {
        "label": "Fast Trance & Eurodance Revival (142–148 BPM)",
        "tracks": [
            ("Marlon Hoffstadt",    "It's That Time",               None),
            ("Marlon Hoffstadt",    "Call Me",                      None),
            ("DJ HEARTSTRING",      "Bae",                          None),
            ("DJ HEARTSTRING",      "Can't Stop The Night",         None),
            ("Southstar",           "Miss You",                     None),
            ("Funk Tribu",          "Phonky Tribu",                 None),
            ("Malugi",              "Reach Out",                    None),
            ("Pegassi",             "Bad Girl",                     None),
            ("Narciss",             "Physical",                     None),
            ("John Summit",         "Where You Are",                None),
        ]
    },

    "8_HARD_TECHNO_SCHRANZ": {
        "label": "Hard Techno & Schranz — Finale Eskalation (150–160 BPM)",
        "tracks": [
            ("Klangkuenstler",      "Die Welt brennt",              None),
            ("Klangkuenstler",      "Himmelreich",                  None),
            ("Nico Moreno",         "Purple Widow",                 None),
            ("Nico Moreno",         "Techno Music Saved My Life",   None),
            ("Sara Landry",         "Legacy",                       None),
            ("Sara Landry",         "Peer Pressure",                None),
            ("Alignment",           "Attack",                       None),
            ("Alignment",           "Old School",                   None),
            ("I Hate Models",       "Toro",                         None),
            ("Kobosil",             "Full of Fire",                 None),
            ("Viper Diva",          "Born Slippy Techno",           "Viper Diva Born Slippy techno rework"),
        ]
    },
}

def all_tracks():
    """Gibt alle Tracks als flache Liste zurück: (phase_key, artist, title, search_query)"""
    result = []
    for phase_key, phase in PHASES.items():
        for artist, title, hint in phase["tracks"]:
            query = hint if hint else f"{artist} {title}"
            result.append((phase_key, artist, title, query))
    return result

if __name__ == "__main__":
    tracks = all_tracks()
    print(f"Gesamt: {len(tracks)} Tracks\n")
    current_phase = None
    for phase_key, artist, title, query in tracks:
        if phase_key != current_phase:
            current_phase = phase_key
            print(f"\n── {PHASES[phase_key]['label']} ──")
        print(f"  {artist} — {title}")
