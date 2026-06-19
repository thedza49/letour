These two scripts are from an earlier attempt at automated rider import
(ProCyclingStats scraping). Both had bugs (sync_riders.py hardcoded every
rider's price/type; import_riders.py only had 7 hardcoded riders and was
explicitly unfinished). They're parked here, not deleted, in case you want
to revisit scraping later per the shaping doc. For now, models.py seeds a
starter rider pool directly.
