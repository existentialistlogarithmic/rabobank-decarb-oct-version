"""Observed inputs: what official statistics can put under the model's assumptions.

Three modules, one rule. :mod:`data.observed` holds the shared series type and
the caching contract; :mod:`data.eurostat` and :mod:`data.ecb` are providers on
top of it. The rule is that a run must produce identical numbers with the
network switched off, because a model whose output depends on whether a web
service answered this morning is not reproducible.

Nothing here decides anything. These modules supply *inputs*: NPV, ``T*`` and
the trigger are model outputs and no statistical agency publishes them.
"""
