#!/usr/bin/env python3

from scripts.database import database_stats


def main():

    stats = database_stats()

    print()
    print("===================================")
    print("5ibr Database Statistics")
    print("===================================")
    print()

    print(f"Domains    : {stats['domains']}")
    print(f"Vendors    : {stats['vendors']}")
    print(f"Categories : {stats['categories']}")

    print()
    print("Top Vendors")
    print("-----------")

    for vendor, count in stats["top_vendors"]:
        print(f"{vendor:<20} {count}")

    print()
    print("Top Categories")
    print("----------------")

    for category, count in stats["top_categories"]:
        print(f"{category:<20} {count}")
