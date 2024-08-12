#!/usr/local/bin/python3

import sys
import certstream
import tldextract
import re
import argparse
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, update
from declarative_sql import Subdomain, Base
from sqlalchemy.orm import sessionmaker

@contextmanager
def suppress_stderr():
    original_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    try:
        yield
    finally:
        sys.stderr.close()
        sys.stderr = original_stderr

def print_callback(message, context):
    subdomains_to_ignore = [
        "www",
        "*",
        "azuregateway",
        "direwolf",
        "devshell-vm-",
        "device-local",
        "-local",
        "sni"
    ]

    subdomains_regex_to_ignore = [
        "[a-f0-9]{24}",
        "device[a-f0-9]{7}-[a-f0-9]{8}",
        "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
        "device-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
    ]

    if message['message_type'] == "heartbeat":
        return

    if message['message_type'] == "certificate_update":
        domains = message['data']['leaf_cert']['all_domains']
        domain_filter = parse_args().filter

        for domain in domains:
            extract = tldextract.extract(domain)
            computed_domain = extract.domain + '.' + extract.suffix

            if domain_filter is None or (domain_filter is not None and computed_domain in domain_filter):
                subdomain = extract.subdomain if domain_filter is None else domain

                if len(subdomain) > 0:
                    multi_level = subdomain.find(".")

                    if multi_level != -1 and domain_filter is None:
                        subdomain_split = subdomain.split('.', 1)
                        subdomain = subdomain_split[0]

                    i = 0
                    for search in subdomains_to_ignore:
                        if search in subdomain:
                            i += 1
                    
                    for search in subdomains_regex_to_ignore:
                        if re.search(search, subdomain):
                            i += 1

                    if i == 0:
                        engine = create_engine('sqlite:///subdomains.db')
                        Base.metadata.bind = engine
                        Session = sessionmaker()
                        Session.configure(bind=engine)
                        session = Session()

                        subdomain_exists = session.query(Subdomain).filter_by(subdomain=subdomain).first()
                        
                        if not subdomain_exists:
                            subdomain_new = Subdomain(subdomain=subdomain, count=1)
                            session.add(subdomain_new)
                            session.commit()
                            print("[+] " + subdomain)
                        
                        if subdomain_exists:
                            counter = subdomain_exists.count + 1
                            session.query(Subdomain).filter(Subdomain.id == subdomain_exists.id).\
                                update({'count': counter})
                            session.commit()
                            if counter % 50 == 0:
                                print("[#] " + subdomain + " (seen " + str(counter) + " times)")

def dump():
    engine = create_engine('sqlite:///subdomains.db')
    Base.metadata.bind = engine
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()

    subdomains = session.execute("SELECT * FROM subdomains ORDER BY count DESC").fetchall()

    if len(subdomains) > 0:
        with open("names.txt", "w") as f:
            for subdomain in subdomains:
                f.write(subdomain.subdomain)
                f.write("\r\n")
    sys.exit('names.txt has been written')

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dump', help="Dump the list of collected subdomains to names.txt", action='store_true')
    parser.add_argument('-f', '--filter', help="A space-separated list of domain names to filter for (e.g. 'google.com' or 'tesco.co.uk tesco.com harrods.com'). BE PATIENT.", nargs='+')
    parser.add_argument('-F', '--file', help="A file containing a list of domains to filter for, one per line.")
    
    args = parser.parse_args()
    
    if args.file:
        with open(args.file, 'r') as f:
            args.filter = [line.strip() for line in f]
    
    return args

def main():
    with suppress_stderr():
        certstream.listen_for_events(print_callback, url='wss://certstream.calidog.io/')

def interactive():
    args = parse_args()

    if args.dump:
        dump()

    main()

if __name__ == "__main__":
    interactive()
