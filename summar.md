# Industrial Decarbonisation Investment Timing

# Findings, Sensitivity and Interpretation

## 0. Opening

Good morning.

In this section of my thesis, I want to present the main findings from the investment-timing model and, importantly, discuss how robust those findings are when I change the underlying assumptions.

The central question of the analysis is relatively simple:

> Given an existing steel asset, when is it economically optimal to commit to a transition from a conventional blast furnace to hydrogen-based direct reduced iron and electric arc furnace production?

The important point is that this is not simply a comparison between two technologies.

The firm has an existing asset that generates value today, but it also faces future decisions about reinvestment, carbon costs, hydrogen costs, support, resale value and uncertainty.

Therefore, the firm has an **option to wait**.

Waiting has value because some uncertainty may be resolved and future market conditions may become more favourable. But waiting also has a cost because the existing technology continues to operate and eventually reaches a reline or reinvestment point.

The results therefore try to answer two related questions:

1. **How valuable is the investment opportunity?**
2. **At what carbon price does exercising the investment option become optimal?**

The second question is represented by the **trigger price**.

Throughout the presentation, I will distinguish between:

- **NPV**, which tells us the value of the investment;
- **The trigger**, which tells us the carbon price required to make investment optimal;
- **T\***, which is the optimal commitment year;
- **The crossing year**, which is the year in which the carbon-price path actually crosses the trigger.

A major finding is that these concepts should not be treated as interchangeable.

---

# 1. Base Decision: NPV by Commitment Year

The first result is the NPV by commitment year.

The model evaluates the project under several assumptions.

The baseline scenario is based on the published assumptions, with:

- Hydrogen at €2.60 per kilogram;
- The long-run volatility regime;
- Resale permitted;
- Nominal price basis;
- Lump-sum support of €200 per tonne of capacity.

These assumptions are important because every number on this first page is conditional on them.

The main output is the NPV for committing in each possible year.

In the baseline case, the NPV is:

- €1,252 per tonne of capacity in 2026;
- €1,344 in 2027;
- €1,573 in 2028;
- €1,588 in 2029;
- €1,581 in 2030;
- €1,556 in 2031;
- €1,520 in 2032.

So the maximum occurs in **2029**.

Therefore:

**T\* = 2029**

The important interpretation is that the optimal decision is not necessarily to invest immediately.

The model says that waiting initially increases the value of the opportunity.

From 2026 to 2029, NPV rises substantially.

The intuition is that waiting allows the firm to benefit from a combination of:

- Higher expected carbon prices;
- The value of the existing asset while waiting;
- The option value associated with delaying an irreversible investment.

But after 2029, the value begins to decline.

That tells us that there is an optimal balance between waiting for better conditions and waiting too long.

### The Reline Effect

There is a particularly important feature at **2032**.

The PDF identifies the step at 2032 as the reline point. At this point, the economics change because the avoided reinvestment changes from an avoided cost into a paid cost.

This is crucial.

If the firm invests in the transition before the reline, it can avoid spending the money associated with relining the existing blast furnace.

Once that reline has already occurred, the firm has effectively committed additional capital to the existing technology.

So the economics are discontinuous around this point.

This is why the NPV falls sharply between 2032 and 2033:

- 2032: €1,520
- 2033: €1,062

That is not simply a normal year-to-year decline.

It is the effect of the investment calendar.

So one of the broader conclusions is that **investment timing is partly an economic problem and partly a calendar problem**.

---

# 2. How Assumptions Change the Value

The first page also compares four specifications:

1. The published baseline;
2. Adding a load factor of 0.85;
3. Adding hot-metal conversion efficiency, κ = 0.94;
4. Moving from nominal to real prices.

This is useful because it shows how quickly the estimated value can change when we move away from the baseline assumptions.

For example, in 2029:

- Baseline NPV = €1,588;
- With load factor = €1,285;
- With hot-metal κ = 0.94 = €1,150;
- With real prices = €722.

So there is a clear cumulative reduction.

The most dramatic change here comes from the **real versus nominal price basis**.

Under the real-price specification, the 2029 NPV falls to €722.

That is a reduction of more than half compared with the baseline.

This is important for interpretation because it tells us that the headline NPV is not universally robust to accounting or price-basis assumptions.

However, this does **not automatically mean that the entire model is unstable**.

It means different assumptions affect different parts of the model differently.

That distinction becomes very important later when I discuss the sensitivity analysis.

---

# 3. Carbon Price Path and the Investment Trigger

The next question is:

> When should the firm actually invest?

The model gives a trigger carbon price of approximately:

**€109.52 per tonne of CO₂**

under the long-run volatility regime.

The carbon-price path starts at:

- €76 in 2026;
- €85 in 2027;
- €94 in 2028;
- €103 in 2029;
- €112 in 2030.

Therefore, the carbon-price path crosses the €109.52 trigger in **2030**.

But there is an interesting result:

**T\* = 2029, while the crossing year is 2030.**

At first this might look inconsistent.

It is not.

The model explicitly explains that the difference between T\* and the crossing year is the **option premium expressed in time**.

The key distinction is:

- **T\*** is the optimal commitment year from the option model.
- **Crossing year** is when the exogenous carbon-price path physically reaches the trigger.

Because the decision is forward-looking, the optimal exercise date does not necessarily have to equal the first year in which the deterministic carbon path crosses the trigger.

This is one of the reasons an option framework is more informative than simply saying:

> Invest when carbon reaches X.

The option model incorporates the value of waiting and uncertainty.

---

# 4. The Cumulative Stress Ladder

The next analysis is the cumulative stress ladder.

This is one of the most useful parts of the sensitivity analysis because instead of changing every assumption simultaneously, I progressively introduce corrections.

The baseline is:

**€1,588 NPV and T\* = 2029.**

### Step 1: Load Factor of 0.85

NPV falls from €1,588 to approximately:

**€1,294**

T\* moves from 2029 to:

**2030**

Reducing utilisation makes the project less valuable and delays the optimal investment.

### Step 2: Hot-Metal Factor κ = 0.94

NPV falls further to:

**€1,166**

T\* remains:

**2030**

This correction further reduces value but does not change timing.

### Step 3: Real Rather than Nominal Prices

NPV falls to:

**€754**

T\* moves to:

**2031**

This assumption has a large effect on value and timing.

### Step 4: Hydrogen at €8.29/kg

Now the result changes dramatically.

NPV becomes approximately:

**−€49 per tonne of capacity**

There is no finite optimal investment year within the model horizon.

The table describes this as **"beyond."**

This means the investment is no longer attractive under those assumptions.

Hydrogen price is therefore not a second-order assumption.

It can determine whether the project is economically viable at all.

### Resale Switched Off

When resale is switched off, the result remains approximately:

**−€49**

This tells us that under this highly stressed hydrogen-price scenario, negative hydrogen economics dominate the resale effect.

### Support Treated as a Stream

Finally, treating support as a stream pushes NPV further negative:

**−€58**

The cumulative ladder demonstrates that the model is highly sensitive to some commercial assumptions, but not equally sensitive to every assumption.

---

# 5. Volatility Regimes

The next result concerns volatility.

The trigger is:

- **CfD:** €89.06/tCO₂
- **Long-run:** €109.52/tCO₂
- **Crisis:** €139.84/tCO₂
- **Realised:** €202.52/tCO₂

The corresponding crossing years are:

- 2028 for the CfD regime;
- 2030 for long-run;
- 2035 for crisis;
- 2043 for realised volatility.

This is a very important result because it shows that volatility does not primarily change value in this model.

Instead, volatility changes the **threshold required for investment**.

That distinction becomes formalised in the lever map.

---

# 6. Understanding the Sensitivity / Lever Map

This is probably the most important section to explain clearly during the defence.

The model separates parameters according to whether they affect:

1. **Value only**
2. **Threshold only**
3. **Both value and threshold**

The sensitivity table uses two quantities:

- **dNPV %**
- **d Trigger %**

The "d" means a **change** or sensitivity effect.

For example:

> Load factor −0.10 → NPV −14.646%

This means reducing the load factor by 0.10 produces approximately a 14.65% reduction in NPV relative to the baseline.

It is not reporting the derivative itself.

The same logic applies to the trigger column.

## A. Value-Only Levers

### 1. Load Factor

- NPV: −14.646%
- Trigger: 0.000%

Utilisation changes profitability but not the carbon-price threshold.

### 2. Support

Doubling support:

- NPV: +11.609%
- Trigger: 0.000%

Support increases value but does not move the trigger.

### 3. Resale

Switching resale from w = 1 to w = 0:

- NPV: −6.130%
- Trigger: 0.000%

Value changes while the threshold remains unchanged.

### 4. Price Basis

Nominal to real prices:

- NPV: −34.589%
- Trigger: 0.000%

This is the largest value-only effect.

### 5. Policy Vintage

- NPV: +0.589%
- Trigger: 0.000%

A relatively small effect.

---

# 7. Threshold-Only Levers

### Volatility → Crisis

- NPV: 0.000%
- Trigger: +27.694%

Higher uncertainty increases the threshold required for investment.

### Volatility → CfD

- NPV: 0.000%
- Trigger: −18.674%

The trigger becomes lower.

A policy instrument aimed at reducing uncertainty can affect the investment threshold without necessarily increasing underlying NPV.

---

# 8. Levers That Move Both Value and Threshold

### Capex +20%

- NPV: −6.836%
- Trigger: +9.836%

Higher capex reduces value and raises the required carbon-price threshold.

### Hot-Metal Factor κ = 0.94

- NPV: −9.869%
- Trigger: +6.762%

This affects both project economics and the trigger.

### Hydrogen +€0.40/kg

- NPV: −11.108%
- Trigger: +15.027%

Hydrogen price affects both value and threshold.

### Write-Off Share φ = 1.0

- NPV: −2.234%
- Trigger: +9.836%

The impact on the trigger is much larger than the impact on value.

---

# 9. Why the Orthogonal Split Matters

The report describes these groups as **orthogonal**.

The key finding is:

- Five parameters move value but not the trigger;
- Two move the trigger but not value;
- Four move both.

This follows directly from the structure of the trigger equation.

Some parameters mathematically cannot influence the trigger.

For example:

> A grant can improve project value, but it cannot solve a volatility problem.

Conversely:

> A CfD can move the investment threshold, but it cannot automatically improve project NPV.

Therefore, these instruments are complements rather than substitutes.

---

# 10. Hydrogen Price and the Utilisation Sign Flip

The model calculates sensitivity of NPV to load factor:

**dNPV/du**

where:

- NPV is net present value;
- u is utilisation;
- dNPV/du is the marginal change in NPV from changing utilisation.

At low hydrogen prices:

- €2/kg → +1,534.4
- €4/kg → +594.9
- €6/kg → +24.8

Higher utilisation is beneficial.

### The Sign Flip

The model identifies a critical point:

**€6.15/kg hydrogen**

At this point:

**dNPV/du = 0**

Above this price:

- €7.50/kg → −2.8
- €8/kg → −7.2
- €10/kg → −24.5
- €14/kg → −59.2

Above €6.15/kg:

> Running the plant more reduces NPV.

This is the "asset-to-liability" inversion described in the report.

---

# 11. Why Does Utilisation Become a Liability?

The load factor multiplies the operating flow.

That operating flow contains both:

- The benefit from avoiding carbon costs;
- The cost associated with hydrogen and operations.

When avoided carbon costs exceed hydrogen penalties:

> Higher utilisation → higher NPV.

When hydrogen costs become sufficiently high:

> Higher utilisation → lower NPV.

The report estimates a critical point at:

**€6.15/kg hydrogen**

with an implied operating penalty of approximately:

**−€311/t per year**

The report compares this with a May 2026 Platts assessment of:

**€8.29/kg**

This is above the €6.15/kg flip point.

Under the corrected real-price specification, the model therefore suggests that operating less may be economically preferable.

A minimum-utilisation covenant could theoretically point in the wrong direction under such economics.

---

# 12. Investment Timing and the Reline Calendar

The next analysis asks:

> What happens when we vary the age of the existing asset?

The result is very interesting.

For assets aged 0 to 15 years in 2026, the optimal commitment year is determined primarily by economics.

But from age 16 onward:

**T\* equals the reline year exactly.**

The report describes this as the **capture region**.

### Age 16

- Reline year = 2030
- T\* = 2030
- NPV = €1,343

### Age 17

- Reline year = 2029
- T\* = 2029
- NPV = €1,365

### Age 18

- Reline year = 2028
- T\* = 2028
- NPV = €1,369

The highest value is reached at:

**Age 18, NPV ≈ €1,369/t capacity**

The model therefore suggests neither investing in the newest plant nor keeping the old plant indefinitely.

Instead, there is a specific point in the asset lifecycle where the decision becomes closely tied to the reline schedule.

---

# 13. Discount-Rate Sensitivity

The next robustness test concerns the real discount rate.

The model evaluates rates from:

**6% to 10%**

### At 6%

- Break-even multiple = 11.56
- Option multiple = 8.275
- Trigger = €95.62

### At 8%

- Break-even multiple = 30.50
- Option multiple = 3.591
- Trigger = €109.52

### At 10%

- Break-even multiple = 46.67
- Option multiple = 2.643
- Trigger = €123.36

The trigger rises from:

**€95.62 → €123.36**

Approximately a 29% increase.

However, the report makes a deeper point.

The break-even price changes dramatically.

From 6% to 10%, it increases by approximately:

**304%**

At the same time, the option multiple falls by approximately:

**68%**

These effects partially cancel out.

This is why the trigger moves by only around:

**29%**

The report therefore describes this as:

> Cancellation, not robustness.

A result can appear stable because two unstable components move in opposite directions.

---

# 14. Why Real Prices Change NPV but Not the Trigger

Changing the price path from nominal to real terms reduces NPV by approximately one third.

Yet the trigger changes by:

**0%**

This is not a bug.

Deflating the price path changes the value calculation but leaves the relevant difference:

**r − μ**

unchanged.

Therefore, the trigger remains unchanged.

This is another example of why value and threshold should be treated as separate objects.

---

# 15. Correlation Matrix

The model evaluates:

**81 scenarios**

The strongest relationship is:

**T\* versus NPV₀ = −0.95**

Later commitment years are strongly associated with lower NPV.

There is also:

- T\* vs Trigger = +0.88
- T\* vs Crossing Year = +0.87

The strongest relationship in the matrix is:

**Trigger vs Crossing Year = +0.99**

A higher trigger requires the carbon-price path to move further before crossing it.

---

# 16. Why the Correlation Matrix Can Be Misleading

The matrix shows:

**NPV₀ vs Trigger = −0.87**

At first glance, this appears to suggest that value and threshold are strongly linked.

However, this does not contradict the earlier orthogonal sensitivity results.

The two analyses answer different questions.

The orthogonal sensitivity analysis asks:

> What happens when a specific parameter changes?

The correlation matrix asks:

> How do outputs move together across the selected scenario set?

Hydrogen price and capex affect both value and trigger.

Because the scenario ensemble varies these parameters, strong correlations emerge.

The report therefore describes the observed relationship as an artefact of sampling design.

The correlation is a property of the **sample**.

The orthogonal separation is a property of the **model structure**.

---

# 17. Overall Findings

## Finding 1: Value and Threshold Are Structurally Different

Five parameters affect value only.

Two affect threshold only.

Four affect both.

Different economic and policy interventions therefore operate through different channels.

## Finding 2: Hydrogen Price Creates a Critical Operating Inversion

At:

**€6.15/kg**

the marginal effect of utilisation becomes zero.

Above this point, more utilisation reduces NPV.

## Finding 3: The Calendar Eventually Dominates the Economics

After approximately 16 years of asset age, T\* equals the reline year.

The reline schedule becomes a major determinant of investment timing.

## Finding 4: Discount-Rate Robustness Is Partly an Illusion

The trigger moves only around 29%.

However:

- Break-even component increases by about 304%;
- Option multiple decreases by about 68%.

The apparent stability comes from cancellation.

## Finding 5: Correlation Does Not Establish Causality

Correlations depend on which parameters are varied.

Parameter-level sensitivity analysis is therefore more informative for identifying intervention channels.

---

# 18. Final Conclusion

The main contribution of this analysis is not simply a single investment year or one carbon-price trigger.

The more important result is the **structure of the decision**.

Investment timing is determined by a combination of:

- Carbon prices;
- Hydrogen prices;
- Asset utilisation;
- Capital expenditure;
- Support;
- Volatility;
- Resale value;
- The physical investment calendar.

These variables do not all operate through the same mechanism.

Some change project value.

Some change the threshold.

Some change both.

This distinction matters for policy interpretation.

If the problem is inadequate project value, increasing support may help.

If the problem is uncertainty and a high trigger, a mechanism such as a CfD may be more relevant.

Increasing support cannot necessarily solve a volatility problem.

Similarly, reducing uncertainty does not automatically solve poor project economics.

The hydrogen-price result adds another layer.

Once hydrogen becomes sufficiently expensive, utilisation itself can become a liability rather than an asset.

Finally, the reline result shows that investment timing is not purely a market-forecasting problem.

At sufficiently advanced asset ages, the physical calendar starts to dominate.

The overall message is:

> **The investment decision should not be reduced to a single carbon-price threshold. It is a real-options decision in which value, threshold, uncertainty and asset timing interact, but they do not necessarily respond to the same variables.**

This is why the sensitivity analysis is important.

It tells us not simply whether the headline number changes, but **which part of the decision changes, by how much, and through which economic mechanism.**

---

# Quick Defence Cheat Sheet

### What does T\* mean?

T\* is the optimal commitment year produced by the investment-timing model. It is the year that maximises the value of exercising the investment option.

### What is the trigger?

The trigger is the carbon price at which the investment option becomes optimal to exercise under the model's assumptions.

### Why isn't T\* equal to the crossing year?

Because T\* is the optimal decision from the option model, whereas the crossing year is when the assumed carbon-price path actually reaches the trigger. The difference represents the option premium expressed in time.

### What does dNPV/du mean?

It is the marginal sensitivity of NPV to utilisation. It tells us whether increasing the load factor raises or lowers NPV.

### Why is dNPV/du negative above €6.15/kg?

Because sufficiently high hydrogen prices make the hydrogen operating penalty larger than the avoided carbon-cost benefit. Increasing utilisation therefore increases exposure to a negative operating flow.

### Is the model robust?

It depends on the definition of robustness. The trigger is relatively robust to several value-side assumptions, while project value itself remains highly sensitive to assumptions such as hydrogen price and price basis.

### Why does real versus nominal change NPV but not the trigger?

Because the real-price transformation changes value calculations but leaves the relevant r − μ term unchanged.

### Why shouldn't we trust the correlation matrix?

The matrix is descriptively correct for the 81 scenarios, but it does not establish structural causality. Correlations depend on the scenario design.

### What is the most important sensitivity?

On the value side, the largest reported effect is the nominal-to-real price-basis change:

**−34.589% NPV**

On the trigger side, the largest effect is the crisis volatility regime:

**+27.694% Trigger**

### What is your strongest finding?

The strongest finding is the separation between project value and investment threshold. Different economic and policy levers affect different parts of the investment decision.

---

# Important Qualification

The final page explicitly states that this is an **explanatory framework rather than investment advice**.

It also cautions that:

- The cost-side learning rate is calibrated rather than externally sourced;
- Ladder rows 4 to 7 do not reproduce the published table.

Therefore, these findings should not be interpreted as precise forecasts.

Instead, the purpose is to understand the economic mechanisms and the sensitivity of investment timing to underlying assumptions.

The results should therefore be interpreted as a **modelling framework** rather than a precise forecast of actual investment dates or future hydrogen and carbon prices.
