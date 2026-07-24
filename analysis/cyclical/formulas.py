"""Machine-readable registry of the public formulas used by the framework."""
from __future__ import annotations

FORMULA_REGISTRY = (
    {
        "COMPONENT": "KEY",
        "STATUS": "VERIFIED FORMULA",
        "FORMULA": "MOM = (WMA4(Close) - WMA12(Close)) / WMA4(Close) * 100; normalize positive/negative MOM changes over 5 periods; EMA3 smoothing.",
        "SOURCE": "CM_Prt.pdf; CM_MetaStock.pdf",
        "IMPLEMENTATION": "caruso_analysis.calculate_key",
        "LIMITATION": "Platform initialization details may create small warm-up differences.",
    },
    {
        "COMPONENT": "XTL",
        "STATUS": "VERIFIED FORMULA / PLATFORM CONVENTION",
        "FORMULA": "XTL = WMA3(Stochastic(5,3)) * 2 - 100.",
        "SOURCE": "CM_Prt.pdf; CM_MetaStock.pdf",
        "IMPLEMENTATION": "caruso_analysis.calculate_xtl",
        "LIMITATION": "Stochastic(5,3) uses the standard raw %K(5) followed by SMA3 because the papers do not expose the platform's internal convention.",
    },
    {
        "COMPONENT": "COMPOSITE MOMENTUM",
        "STATUS": "VERIFIED FORMULA",
        "FORMULA": "Composite = WMA2((2 * KEY + XTL) / 3).",
        "SOURCE": "CM_Prt.pdf; CM_MetaStock.pdf",
        "IMPLEMENTATION": "caruso_analysis.calculate_composite_momentum",
        "LIMITATION": "Dependent on the declared XTL stochastic convention.",
    },
    {
        "COMPONENT": "U/A/D/T PHASES",
        "STATUS": "DOCUMENTED RULE",
        "FORMULA": "UP: CM < 0 and rising; ADVANCING: CM >= 0 and rising; DOWN: CM >= 0 and falling; TERMINATING: CM < 0 and falling.",
        "SOURCE": "La Metodologia Ciclica.pdf",
        "IMPLEMENTATION": "analysis.cyclical.states.phase_series",
        "LIMITATION": "Flat slopes are handled deterministically by the software.",
    },
    {
        "COMPONENT": "12-CASE TACTICAL MATRIX",
        "STATUS": "DOCUMENTED RULE",
        "FORMULA": "Quarterly direction × monthly direction × weekly turn maps to BUY, SELL SHORT or TAKE PROFIT plus rating.",
        "SOURCE": "La Metodologia Ciclica.pdf",
        "IMPLEMENTATION": "caruso_analysis.STRATEGY_MATRIX",
        "LIMITATION": "Execution timing and Long-only versus Long/Short are research conventions, not proprietary rules.",
    },
)
