# POST HOC frontier diagnostic (not a decision input): fixed vs online classes across target FER, cost = timing-reference s

dev = frames 0-299 (selection), test = 300-599. (a) both classes selected on dev with dev FER <= level; (b) online selected with
dev FER <= level - 0.02 (margin rule), fixed with <= level; (c) in-sample test frontier (optimistic for both, more for online).

## L16

| level | (a) fixed test cost/FER | (a) online test cost/FER | (a) saving | (b) online+margin cost/FER | (b) saving | (c) fixed | (c) online | (c) saving |
|---|---|---|---|---|---|---|---|---|
| 0.05 | - | - | - | - | - | - | - | - |
| 0.075 | - | - | - | - | - | 0.671 | 0.528 | 0.212 |
| 0.1 | 0.671 / 0.073 | 0.496 / 0.100 | 0.261 | - | - | 0.631 | 0.477 | 0.244 |
| 0.125 | 0.631 / 0.093 | 0.436 / 0.137 | 0.308 | 0.490 / 0.100 | 0.223 | 0.631 | 0.446 | 0.293 |
| 0.15 | 0.631 / 0.093 | 0.429 / 0.147 | 0.320 | 0.433 / 0.140 | 0.313 | 0.496 | 0.416 | 0.163 |

## L20

| level | (a) fixed test cost/FER | (a) online test cost/FER | (a) saving | (b) online+margin cost/FER | (b) saving | (c) fixed | (c) online | (c) saving |
|---|---|---|---|---|---|---|---|---|
| 0.15 | - | - | - | - | - | 1.136 | 0.903 | 0.205 |
| 0.2 | 0.993 / 0.200 | 0.768 / 0.190 | 0.226 | 0.828 / 0.180 | 0.166 | 0.993 | 0.721 | 0.274 |
| 0.25 | 0.935 / 0.220 | 0.646 / 0.233 | 0.308 | 0.718 / 0.213 | 0.232 | 0.935 | 0.615 | 0.342 |

