"""Studies that run on top of the model without changing it.

:mod:`analysis.findings` derives the structural results from the model alone.
:mod:`analysis.grounding` puts every checkable input next to the statistic that
bears on it and states a verdict. :mod:`analysis.sourcing` ties the hydrogen
price and the clean-route emission intensity into the single parameter they
physically are, and reports what that costs.

None of these modules mutates a registered default. They report; the decision
to change an input stays with whoever reads the report.
"""
