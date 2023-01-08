#!/usr/bin/env python3

import argparse
import json
import logging
import logging.handlers
import os
import subprocess
import sys
import time
import urllib
import urllib.parse
import urllib.request
import yaml

STATUS = 0
dev_null = open("/dev/null", 'w')
verbose_output = dev_null

def parse_args():
    parser = argparse.ArgumentParser(prog="CloudFlare DDNS", description="A simple Python script to keep one or more CloudFlare DNS entries up to date with your public IP address")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-c", "--config-file", required=False, default="/etc/ddns/domains.yaml", dest="config_file")
    return parser.parse_args()

def vprint(*args, **kwargs):
    print(*args, file=verbose_output, **kwargs)

def print_output():
    output =  '# HELP public_ip_address_changed Has the public IP address changed (1 = changed, 0 = unchanged\n'
    output += '# TYPE public_ip_address_changed gauge\n'
    for domain in domains:
        output += 'ddns_public_ip_address_changed{{cached_address="{0}", new_address="{1}"}} {2}\n'.format(domain['cached_ip'], live_ip, ip_changed)
    output += '# HELP ddns_records_updated Status of DNS records being updated in Cloudflare (1 = changed, 0 = unchanged)\n'
    output += '# TYPE ddns_records_updated gauge\n'
    for domain in domains:
        records = domain['records']
        for record in records:
            output += 'ddns_records_updated{{cloudflare_domain="{0}",cloudflare_zone_id="{1}",cloudflare_record_id="{2}",cloudflare_record_type="A",cloudflare_record_name="{3}"}} {4}\n'.format(domain['name'], domain['zone_id'], record['record_id'], record['name'], record['record_changed'])
    output += '# HELP ddns_script_status Status of DDNS shell script (1 = success, 0 = failure)\n'
    output += '# TYPE ddns_script_status gauge\n'
    output += "ddns_script_status {0}\n".format(STATUS)
    output += '# HELP ddns_script_last_runtime_epoch Epoch time the DDNS script last executed\n'
    output += '# TYPE ddns_script_last_runtime_epoch gauge\n'
    output += "ddns_script_last_runtime_epoch {0}\n".format(exec_time)
    print(output)

if __name__ == "__main__":

    args = parse_args()
    verbose_output = dev_null if not args.verbose else sys.stderr
    vprint("[+] Using config file: '{0}'".format(args.config_file))
    with open(args.config_file, 'r') as stream:
        try:
            yaml_config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    domains = yaml_config['domains']

    live_ip = subprocess.check_output(['/usr/bin/dig', '+short', 'myip.opendns.com', '@resolver1.opendns.com']).decode('ascii').rstrip()

    exec_time = int(time.time())

    cache_file_path = yaml_config['cache_file'] if 'cache_file' in yaml_config else "/etc/ddns/cache.txt"

    for domain in domains:
        vprint("[+] Checking domain: '{0}'".format(domain['name']))
        records = domain['records']


        vprint("[+] Checking if cache file defined for this domain exists: '{0}'".format(domain['cache_file']))
        if os.path.exists(cache_file_path):
            vprint("[+] Cache file exists")
            with open(cache_file_path, 'r') as cache_file:
                domain['cached_ip'] = cache_file.readline()
        else:
            vprint("[+] Cache file does not exist")
            domain['cached_ip'] = None

        if live_ip == domain['cached_ip']:
            ip_changed = 0
            STATUS = 1
            for record in records:
                record['record_changed'] = 0
        else:
            ip_changed = 1
            vprint("[+] IP address has changed; updating DNS records")
            with open(cache_file_path, 'w') as cache_file:
                cache_file.write(live_ip)

            api_url = "https://api.cloudflare.com/client/v4/zones/{0}/dns_records/".format(domain['zone_id'])
            headers_json = {
                    "Authorization": "Bearer {0}".format(yaml_config['auth_key']),
                    "Content-Type": "application/json"
                }
            for record in records:
                url = api_url + record['record_id']
                data = {
                        "type": "A",
                        "name": record['name'],
                        "content": live_ip,
                        "proxied": True,
                        "ttl": 1
                    }
                data_bytes = bytes(json.dumps(data), encoding='utf-8')
                auth_string = '{0}'.format(yaml_config['auth_key'])
                vprint("[+] Request URL: {0}".format(url))
                vprint("[+] Request data: {0}".format(data_bytes))
                vprint("[+] Request headers: {0}".format(headers_json))
                req = urllib.request.Request(url, method="PUT", data=data_bytes, headers=headers_json)
                try:
                    with urllib.request.urlopen(req) as response:
                        response_json = json.loads(response.read())
                        vprint(json.dumps(response_json))
                except urllib.error.HTTPError as exc:
                    vprint(vars(exc))
                    vprint(exc)
                record['record_changed'] = 1

            STATUS = 1

    print_output()
