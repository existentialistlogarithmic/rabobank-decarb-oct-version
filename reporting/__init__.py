"""Generated deliverables: pages, tables and the provenance register.

Everything here is written from the model at build time, so no figure or
citation can drift from the code that produced it. :mod:`reporting.sources` is
the one that can fail the run - it regenerates ``SOURCES.md`` from the
provenance register and returns non-zero if any citation quotes a value the
model no longer uses.
"""
