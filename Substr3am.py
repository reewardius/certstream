#!/usr/local/bin/python3

import sys
import certstream
import tldextract
import re
import argparse
import os
from contextlib import contextmanager

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

        unique_subdomains = set()  # Set to store unique subdomains

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
                        # Add the subdomain to the set
                        if subdomain not in unique_subdomains:
                            unique_subdomains.add(subdomain)
                            # Output the subdomain to the console
                            print("[+] " + subdomain)

def dump():
    # Not used anymore, remove if not needed
    sys.exit('Dump functionality removed')

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
