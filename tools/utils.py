#! /usr/bin/env python
#-*- coding: utf-8 -*-

import os, atexit
from xml.sax import make_parser, handler

################################################################################

root_folder       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
allowed_languages = ["en", "fr", "nl", "de"]
translation_file  = os.path.join(root_folder, "config/translate.txt")
config_file       = os.path.join(root_folder, "config/config.xml")
pg_user           = "osmose"
pg_base           = "osmose"

################################################################################

def get_dbconn():
    import psycopg2.extras
#    return psycopg2.connect(host="localhost", database = pg_base, user = pg_user, password = pg_pass)
    db_string = "host='localhost' dbname='%s' user='%s' password='%s'" % (pg_base, pg_user, pg_pass)
    conn = psycopg2.extras.DictConnection(db_string)
    psycopg2.extras.register_hstore(conn)
    return conn

def pg_escape(text):
    if type(text) == int:
        return str(text)
    return text.replace(u"'", u"''").replace(u'\\',u'\\\\')

def get_language():
    if "HTTP_ACCEPT_LANGUAGE" in os.environ:
        lg = os.environ["HTTP_ACCEPT_LANGUAGE"]
        lg = lg.split(",")
        lg = [x.split(";")[0] for x in lg]
        lg = [x.split("-")[0] for x in lg]
        lg = [x for x in lg if x in allowed_languages]
        if lg:
            lg.append(allowed_languages[0])
            res = []
            for l in lg:
                if not l in res:
                    res.append(l)
            return res
    return allowed_languages

def get_sources(lang = get_language()):
    if lang not in allowed_languages:
        lang = allowed_languages[0]
    conn = get_dbconn()
    curs = conn.cursor()
    curs.execute("SELECT source, update, comment, contact FROM dynpoi_source;")
    config = {}
    for res in curs.fetchall():
        src = {}
        src["id"]         = str(res["source"])
        src["updatecode"] = str(res["update"])
        src["comment"]    = str(res["comment"])
        src["contact"]    = str(res["contact"])        
        config[src["id"]] = src
    return config

def get_categories(lang = get_language()):
    result = []
    conn = get_dbconn()
    curs1 = conn.cursor()
    curs2 = conn.cursor()
    curs1.execute("SELECT categ, menu FROM dynpoi_categ ORDER BY categ")
    for res1 in curs1.fetchall():
        res = {"categ":res1[0], "menu": "no translation", "item":[]}
        for l in lang:
            if l in res1[1]:
                res["menu"] = res1[1][l].decode('utf8')
                break
        curs2.execute("SELECT item, menu, marker_color, marker_flag FROM dynpoi_item WHERE categ = %d ORDER BY item"%res1[0])
        for res2 in curs2.fetchall():
            res["item"].append({"item":res2[0], "menu":"no translation", "marker_color":res2[2], "marker_flag":res2[3]})
            for l in lang:
                if res2[1] and l in res2[1]:
                    res["item"][-1]["menu"] = res2[1][l].decode('utf8')
                    break

        result.append(res)
    return result

###########################################################################
## templates

def show(s):
    print s.encode("utf8")

def N_(message):
    return message

def print_template(filename, rules = None):
    page = open(os.path.join(root_folder, "config", filename)).read().decode("utf8")
    if rules:
        for x in rules:
            page = page.replace("#%s#"%x, rules[x].strip())
    print page.encode("utf8")

def print_header(translate = None, title = N_("OsmOse - OpenStreetMap Oversight Search Engine")):
    if not translate:
        translate = translator()
    rules = { "title" : _(title) }
    print_template("head.tpl", rules)

def print_tail():
    print_template("tail.tpl")

###########################################################################
## translation

class translator:
    
    def __init__(self, language = get_language(), translation = translation_file):

        self.languages = language

        import gettext
        gettext.translation('osmose-frontend',
                            localedir=os.path.join(root_folder, "po", "mo"),
                            languages=language
                           ).install(unicode=1)

    def select(self, res, no_translation = ""):
        # res is a dictionnary of possible translations, given by a SQL query
        if not res:
            return ""
        for l in self.languages:
            if l in res:
                return res[l].decode("utf8")
        return no_translation
