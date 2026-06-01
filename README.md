# Home Electronics Store Sales Management System

A Python solution to a competitive programming problem from the **LINE Yahoo internship selection process**.

The system simulates a sales management platform for a home electronics store,
enforcing a configurable minimum profit margin (`rate`) on all discounted transactions.

---

## Problem Overview

The store has `n` salespeople and a catalogue of registered items.
Each item has a **cost price** (原価) and a **list price** (定価).

A salesperson may request permission to sell an item at a price of their choosing.
The system grants or denies the permission based on the following rules:

| Sale price vs. list price | Decision |
|---|---|
| `sale_price > list_price` | ❌ Denied — too expensive |
| `sale_price == list_price` | ✅ Always approved |
| `sale_price < list_price` | ✅ Approved **only if** both margins stay ≥ `rate` |

For discounted sales, the system checks two **hypothetical margins** — as if the sale
completed immediately — for both the individual salesperson and the item itself:

```
margin = (total_sales_revenue - total_cost) / total_sales_revenue
```

### Sale Permission Expiry

An issued sale permission becomes invalid when **any** of the following occur:
1. The same salesperson issues a new sale request.
2. The calendar date changes since the permission was issued.
3. Another salesperson completes a sale of the same item.

---

## Supported Queries

| Query | Type | Description |
|---|---|---|
| `register-item` | Basic | Add a new item to the catalogue |
| `request-sale` | Basic | Request a sale permission |
| `complete-sale` | Basic | Confirm a sale completion |
| `delete-item` | Basic | Remove an item from the catalogue |
| `update-item` | Advanced | Change an item's cost and list price |
| `get-margin-sellers` | Advanced | Rank salespeople by profit margin over a period |
| `get-margin-items` | Advanced | Rank items by profit margin over a period |

---

## Design Notes

### Integer Arithmetic for Margin Comparison

Floating-point comparisons are avoided by converting the margin condition to integer form:

```
(S - C) / S >= rate
  ⟺  100 × (S - C) >= rate_100 × S       (rate_100 = rate × 100, an integer)
```

This eliminates precision errors when comparing against the given rate (up to 2 decimal places).

### Lazy Permission Expiry

Date-change expiry (condition 2) is checked lazily at the point of use
(`complete-sale`, `delete-item`, `update-item`) rather than proactively scanning all
permissions on every query. This keeps each query's complexity proportional to the
number of active permissions for the relevant item.

### Cost Snapshot at Request Time

When `update-item` changes an item's cost, only **future** sale requests are affected.
Permissions already issued retain the cost that was current at request time,
which is recorded in the permission record.

---

## Input Format

```
rate               ← minimum profit margin (e.g. 0.15)
n                  ← number of salespeople
seller_name_1
...
seller_name_n
m                  ← number of queries
query_1
...
query_m
```

Time format: `YYYY/MM/DD-hh:mm:ss`

---

## Running the Solution

```bash
python3 solution.py < tests/sample2_input.txt
```

### Running Tests

```bash
bash run_tests.sh
```

---

## Example

**Input:**
```
0.10
2
Alice
Bob
6
register-item: 2024/06/01-09:00:00 TV 80000 100000
request-sale: 2024/06/01-10:00:00 1 1 100000
complete-sale: 2024/06/01-10:01:00 1 1
request-sale: 2024/06/01-11:00:00 1 1 90000
complete-sale: 2024/06/01-11:05:00 1 2
get-margin-sellers: 2024/06/01-12:00:00 2024/06/01-00:00:00 2024/06/01-23:59:59
```

**Output:**
```
register-item: 1
request-sale: 1
complete-sale: ok
request-sale: 2
complete-sale: ok
get-margin-sellers:
1 Alice 0.176
2 Bob 0.000
```

Alice sold TV at ¥100,000 and then at ¥90,000 (discounted, but margin still ≥ 10%).
Her period margin: (190,000 − 160,000) / 190,000 ≈ **0.176**.
