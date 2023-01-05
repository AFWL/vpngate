#!/bin/env python3

import requests
import os
import subprocess
import base64
import time
import argparse


def chooseServer(code):
    # Get raw server data from the API and strip carriage returns
    rawServerData = requests.get("https://www.vpngate.net/api/iphone/").text.replace(
        "\r", ""
    )

    # Split raw server data into more manageable lists of servers
    parsedServerData = [line.split(",") for line in rawServerData.split("\n")]

    # Get all servers that hold valid VPN data
    availableServers = [
        server
        for server in parsedServerData[2 : len(parsedServerData) - 2]
        if len(parsedServerData) > 1
    ]  # Server data begins at index 2, index 1 is labels. Last 2 indices hold no valid VPN data, so they are excluded

    # Get servers that match the supplied country code, if it is of a valid length
    if len(code) == 2:
        desiredServers = [
            server for server in availableServers if code.upper() == server[6]
        ]

    else:
        print("Invalid country code!")

    try:
        winner = desiredServers[
            0
        ]  # Servers are already sorted by score in descending order, so pick the first one

    except IndexError:
        print(f"Couldn't find any servers for {code.upper()}.")
        exit(1)

    return winner


def createOVPNFile(winner, ovpnConfigPath):
    encodedOVPNData = winner[14]

    # Decode base64 encoded OpenVPN config
    decodedOVPNData = base64.b64decode(encodedOVPNData).decode()

    # Write OpenVPN config to a temporary file
    with open(ovpnConfigPath, "w") as f:
        f.write(decodedOVPNData)
        f.write(
            "\nscript-security 2\nup /etc/openvpn/update-resolv-conf\ndown /etc/openvpn/update-resolv-conf"
        )  # Sets the script-security directive and updates /etc/resolv.conf to avoid DNS leaks. For more information see https://openvpn.net/community-resources/reference-manual-for-openvpn-2-5/


def connect(ovpnConfigPath):
    cmd = ["sudo", "openvpn", "--config", ovpnConfigPath]

    try:
        openvpn = subprocess.Popen(cmd)  # Run OpenVPN as a child process

        # Sleep while OpenVPN is running, this will ensure that control signals are recieved by the child process and not the parent
        while openvpn.poll != 0:
            time.sleep(1)

    except KeyboardInterrupt:
        time.sleep(1)  # Give time for OpenVPN to terminate before exiting

    except:
        raise


if __name__ == "__main__":
    # Argparse
    parser = argparse.ArgumentParser(
        prog="vpngate.py",
        description="A simple client for VPN Gate's public VPN relay network",
    )

    parser.add_argument(
        "code",
        help="Country code of the server you want to connect to, e.g. jp (Japan)",
    )

    parser.parse_args()
    args = parser.parse_args()
    code = args.code

    print("Looking for available servers...")
    winner = chooseServer(code)

    print("Found one!")
    print(f"\nHostname: {winner[0]}")
    print(f"IP Address: {winner[1]}")
    print(f"Latency: {winner[3]} ms")
    print(f"Throughput: {round(float(winner[4]) / 10 ** 6, 2)} Mbps")

    ovpnConfigName = f"vpngate-{winner[0]}.ovpn"
    ovpnConfigPath = os.path.join("/tmp", ovpnConfigName)

    createOVPNFile(winner, ovpnConfigPath)

    print(f"\nLaunching OpenVPN...")
    connect(ovpnConfigPath)

    os.system(f"rm {ovpnConfigPath}")
