# Historical seed separation — read-only lookup

Luna/xhigh inspected supplied screen sources, no receiver execution. The 20 initial exploratory observations use entropy `[20260921,935170,index,component]`, index0..19; screen_fastamp/scalaramp/tangent use0..3, gain_factorial4..11, six_db12..19. Components1/2/3 mean channel/message/noise in the existing generator callback.

The8 native observations use `[20260921,935171,index+1,component]`, index0..7, per tests/screen_native.py. The fair/twofft/block/clean outputs reuse those observations. Existing output audit declares28 unique observations. Old JSON files do not contain a complete per-frame entropy manifest, so this provenance is source-derived rather than a fresh numerical replay.

New A/B namespace940317 differs from both older935170/935171 streams and from previous frozen-campaign namespace480017. New handoff component labels0/1/2 mean message/channel/noise; generator's legacy callback labels require an explicit mapping. Namespace tuples are disjoint; actual finite channel seeds should also be checked for collisions before execution. No old observations enter new denominators.
