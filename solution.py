#!/usr/bin/env python3
"""
[INPUT]: sys.stdin — rate / sellers / items / queries
[OUTPUT]: stdout — one result line per query, margin rankings as multi-line blocks
[POS]: 项目唯一业务文件，完整实现家电销售管理系统所有查询逻辑
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import sys
import math
from datetime import datetime


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def parse_time(s: str) -> datetime:
    return datetime.strptime(s, "%Y/%m/%d-%H:%M:%S")


def fmt_margin(x: float) -> str:
    """Format margin to 3 decimal places using round-half-up."""
    rounded = math.floor(x * 1000 + 0.5) / 1000
    return f"{rounded:.3f}"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def main():
    data = sys.stdin.read().split('\n')
    pos = 0

    rate = float(data[pos]); pos += 1
    # Convert rate to integer (×100) for exact integer comparisons.
    # e.g. rate=0.15  →  rate_100=15
    # margin >= rate  ⟺  100*(S-C) >= rate_100*S
    rate_100 = round(rate * 100)

    n = int(data[pos]); pos += 1

    # sellers[id] = {'name': str, 'sales': [(datetime, sale_price, cost), ...]}
    sellers: dict = {}
    for i in range(1, n + 1):
        name = data[pos].strip(); pos += 1
        sellers[i] = {'name': name, 'sales': []}

    m = int(data[pos]); pos += 1

    # items[id] = {'name', 'cost', 'price', 'deleted', 'sales': [...]}
    items: dict = {}
    active_names: dict = {}   # name → item_id  (non-deleted only)
    next_item_id = 1

    # perms[id] = {'seller_id', 'item_id', 'sale_price', 'cost',
    #              'issued_time', 'status': 'valid'|'expired'|'completed'}
    perms: dict = {}
    next_perm_id = 1

    seller_perm: dict = {}   # seller_id → perm_id of their current valid perm
    item_perms: dict = {}    # item_id   → set of potentially-valid perm_ids

    # -----------------------------------------------------------------------
    # Helper functions
    # -----------------------------------------------------------------------

    def margin_ok(s_total: int, c_total: int) -> bool:
        """Return True if (S-C)/S >= rate, using integer arithmetic."""
        # 100*(S-C) >= rate_100*S
        return 100 * (s_total - c_total) >= rate_100 * s_total

    def mark_expired(pid: int) -> None:
        """Mark a permission as expired and update tracking dicts."""
        perm = perms[pid]
        if perm['status'] != 'valid':
            return
        perm['status'] = 'expired'
        sid = perm['seller_id']
        iid = perm['item_id']
        if seller_perm.get(sid) == pid:
            del seller_perm[sid]
        item_perms[iid].discard(pid)

    def valid_perms_for_item(iid: int, t: datetime) -> set:
        """
        Return currently-valid perm_ids for item iid.
        Lazily expires any that have passed midnight since issuance.
        """
        valid = set()
        for pid in list(item_perms[iid]):
            perm = perms[pid]
            if perm['status'] != 'valid':
                item_perms[iid].discard(pid)
                continue
            if t.date() > perm['issued_time'].date():
                mark_expired(pid)
            else:
                valid.add(pid)
        return valid

    # -----------------------------------------------------------------------
    # Query processing
    # -----------------------------------------------------------------------

    output = []

    for _ in range(m):
        line = data[pos].strip(); pos += 1
        if not line:
            continue
        parts = line.split()
        qtype = parts[0]

        # ── register-item ──────────────────────────────────────────────────
        if qtype == "register-item:":
            # register-item: {time} {name} {cost} {list_price}
            name = parts[2]
            cost = int(parts[3])
            price = int(parts[4])

            if name in active_names:
                output.append("register-item: duplicated item")

            elif not margin_ok(price, cost):
                # (price - cost) / price < rate
                output.append("register-item: too cheap price")

            else:
                iid = next_item_id; next_item_id += 1
                items[iid] = {
                    'name': name, 'cost': cost, 'price': price,
                    'deleted': False, 'sales': []
                }
                active_names[name] = iid
                item_perms[iid] = set()
                output.append(f"register-item: {iid}")

        # ── request-sale ───────────────────────────────────────────────────
        elif qtype == "request-sale:":
            # request-sale: {time} {seller_id} {item_id} {sale_price}
            t   = parse_time(parts[1])
            sid = int(parts[2])
            iid = int(parts[3])
            sp  = int(parts[4])

            item = items.get(iid)
            if item is None or item['deleted']:
                output.append("request-sale: no such item")
                continue

            list_price = item['price']
            cost       = item['cost']

            if sp > list_price:
                output.append("request-sale: too expensive price")
                continue

            if sp < list_price:
                # ── Check hypothetical margins ──────────────────────────
                # Seller margin: assume this sale completes right now
                s_sales = sellers[sid]['sales']
                s_s = sum(s[1] for s in s_sales) + sp
                c_s = sum(s[2] for s in s_sales) + cost

                # Item margin: assume this sale completes right now
                i_sales = item['sales']
                s_i = sum(s[1] for s in i_sales) + sp
                c_i = sum(s[2] for s in i_sales) + cost

                if not margin_ok(s_s, c_s) or not margin_ok(s_i, c_i):
                    output.append("request-sale: too cheap price")
                    continue

            # Expire this seller's previous permission (condition 1)
            if sid in seller_perm:
                mark_expired(seller_perm[sid])

            # Issue new permission
            pid = next_perm_id; next_perm_id += 1
            perms[pid] = {
                'seller_id':   sid,
                'item_id':     iid,
                'sale_price':  sp,
                'cost':        cost,   # snapshot cost at request time
                'issued_time': t,
                'status':      'valid'
            }
            seller_perm[sid] = pid
            item_perms[iid].add(pid)
            output.append(f"request-sale: {pid}")

        # ── complete-sale ──────────────────────────────────────────────────
        elif qtype == "complete-sale:":
            # complete-sale: {time} {seller_id} {perm_id}
            t   = parse_time(parts[1])
            sid = int(parts[2])
            pid = int(parts[3])

            if pid not in perms:
                output.append("complete-sale: no such sale")
                continue

            perm = perms[pid]

            # Check 1: seller must match (before expiry check)
            if perm['seller_id'] != sid:
                output.append("complete-sale: unauthorized operation")
                continue

            # Check 2: date-change expiry (condition 2)
            if t.date() > perm['issued_time'].date():
                mark_expired(pid)

            if perm['status'] != 'valid':
                output.append("complete-sale: permission expired")
                continue

            # ── Record the sale ─────────────────────────────────────────
            iid  = perm['item_id']
            sp   = perm['sale_price']
            cost = perm['cost']   # price at time of request-sale

            sellers[sid]['sales'].append((t, sp, cost))
            items[iid]['sales'].append((t, sp, cost))

            # Mark this permission as completed
            perm['status'] = 'completed'
            if seller_perm.get(sid) == pid:
                del seller_perm[sid]
            item_perms[iid].discard(pid)

            # Expire all other valid permissions for this item (condition 3)
            for other_pid in list(item_perms[iid]):
                mark_expired(other_pid)
            item_perms[iid].clear()

            output.append("complete-sale: ok")

        # ── delete-item ────────────────────────────────────────────────────
        elif qtype == "delete-item:":
            # delete-item: {time} {item_id}
            t   = parse_time(parts[1])
            iid = int(parts[2])

            item = items.get(iid)
            if item is None or item['deleted']:
                output.append("delete-item: no such item")
                continue

            if valid_perms_for_item(iid, t):
                output.append("delete-item: sales in progress")
                continue

            item['deleted'] = True
            active_names.pop(item['name'], None)
            output.append("delete-item: ok")

        # ── update-item ────────────────────────────────────────────────────
        elif qtype == "update-item:":
            # update-item: {time} {item_id} {new_cost} {new_price}
            t         = parse_time(parts[1])
            iid       = int(parts[2])
            new_cost  = int(parts[3])
            new_price = int(parts[4])

            item = items.get(iid)
            if item is None or item['deleted']:
                output.append("update-item: no such item")
                continue

            if valid_perms_for_item(iid, t):
                output.append("update-item: sales in progress")
                continue

            if not margin_ok(new_price, new_cost):
                output.append("update-item: too cheap price")
                continue

            item['cost']  = new_cost
            item['price'] = new_price
            output.append("update-item: ok")

        # ── get-margin-sellers ─────────────────────────────────────────────
        elif qtype == "get-margin-sellers:":
            # get-margin-sellers: {time} {period_start} {period_end}
            start = parse_time(parts[2])
            end   = parse_time(parts[3])

            if end < start:
                output.append("get-margin-sellers: invalid time period")
                continue

            rows = []
            for sid in range(1, n + 1):
                in_period = [s for s in sellers[sid]['sales'] if start <= s[0] <= end]
                s_t = sum(s[1] for s in in_period)
                c_t = sum(s[2] for s in in_period)
                margin = (s_t - c_t) / s_t if s_t > 0 else 0.0
                rows.append((sid, sellers[sid]['name'], margin))

            # Sort: margin descending, then seller ID ascending
            rows.sort(key=lambda x: (-x[2], x[0]))
            lines = ["get-margin-sellers:"]
            lines += [f"{r[0]} {r[1]} {fmt_margin(r[2])}" for r in rows]
            output.append('\n'.join(lines))

        # ── get-margin-items ───────────────────────────────────────────────
        elif qtype == "get-margin-items:":
            # get-margin-items: {time} {period_start} {period_end}
            start = parse_time(parts[2])
            end   = parse_time(parts[3])

            if end < start:
                output.append("get-margin-items: invalid time period")
                continue

            rows = []
            for iid in range(1, next_item_id):
                item = items[iid]
                in_period = [s for s in item['sales'] if start <= s[0] <= end]
                s_t = sum(s[1] for s in in_period)
                c_t = sum(s[2] for s in in_period)
                margin = (s_t - c_t) / s_t if s_t > 0 else 0.0
                rows.append((iid, item['name'], margin))

            # Sort: margin descending, then item ID ascending
            rows.sort(key=lambda x: (-x[2], x[0]))
            lines = ["get-margin-items:"]
            lines += [f"{r[0]} {r[1]} {fmt_margin(r[2])}" for r in rows]
            output.append('\n'.join(lines))

    print('\n'.join(output))


if __name__ == "__main__":
    main()
