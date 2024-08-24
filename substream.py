#!/usr/local/bin/python3

import sys
import certstream
import tldextract
import re
import argparse
import os
import requests
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

def send_to_telegram(telegram_id, telegram_key, message):
    url = f"https://api.telegram.org/bot{telegram_key}/sendMessage"
    data = {
        "chat_id": telegram_id,
        "text": message
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending to Telegram: {e}")

def print_callback(message, context, output_file, telegram_id=None, telegram_key=None):
    subdomains_to_ignore = [
        "*",
        "azuregateway",
        "devshell-vm-",
        "device-local",
        "-local",
        "sni"
    ]

    subdomains_regex_to_ignore = [
        "device[a-f0-9]{7}-[a-f0-9]{8}",
        "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
        "device-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
    ]

    if message['message_type'] == "heartbeat":
        return

    if message['message_type'] == "certificate_update":
        domains = message['data']['leaf_cert']['all_domains']
        domain_filter = parse_args().filter

        unique_subdomains = set()

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
                        if subdomain not in unique_subdomains:
                            unique_subdomains.add(subdomain)
                            output = subdomain
                            if output_file:
                                with open(output_file, 'a') as file:
                                    file.write(output + "\n")
                            else:
                                print(output)
                            
                            if telegram_id and telegram_key:
                                send_to_telegram(telegram_id, telegram_key, output)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filter', help="A space-separated list of domain names to filter for (e.g. 'google.com' or 'tesco.co.uk tesco.com harrods.com'). BE PATIENT.", nargs='+')
    parser.add_argument('-F', '--file', help="A file containing a list of domains to filter for, one per line.")
    parser.add_argument('-o', '--output', help="Output file to save the results.")
    parser.add_argument('-t', '--telegram', help="Send results to Telegram.", action='store_true')
    parser.add_argument('-ti', '--telegram-id', help="Telegram chat ID to send results to.")
    parser.add_argument('-ty', '--telegram-key', help="Telegram bot HTTP API token.")

    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r') as f:
            args.filter = [line.strip() for line in f]
    
    if args.telegram and (not args.telegram_id or not args.telegram_key):
        parser.error("When using -t telegram, --telegram-id or -ti and --telegram-key or -ty must be provided.")

    return args

def main():
    args = parse_args()
    output_file = args.output if args.output else None
    telegram_id = args.telegram_id if args.telegram else None
    telegram_key = args.telegram_key if args.telegram else None

    with suppress_stderr():
        certstream.listen_for_events(lambda message, context: print_callback(
            message, context, output_file, telegram_id, telegram_key), 
            url='wss://certstream.calidog.io/'
        )

if __name__ == "__main__":
    main()
