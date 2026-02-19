# Implementation Guide: Adding Metabolic Studies to studies.json

## Summary of Changes

### NEW STUDIES TO ADD (7 Total)
All studies are in: `/sessions/gracious-beautiful-shannon/mnt/LongevityPath/system/new_metabolic_studies.json`

1. araujo-2019
2. mottillo-2010
3. kramer-2013
4. malmö-2003
5. karelis-2007
6. wang-2023-metabolic
7. reaven-1988
8. glucose-diabetes-collaboration-2011

### EXISTING STUDIES (NO CHANGES)
These studies are already in studies.json and should NOT be modified:
- balkau-2014 ✓
- sarwar-2007 ✓
- gordon dj-1989 ✓
- knowler-2002 ✓

## How to Add Studies to studies.json

### Option 1: Merge JSON Files (Recommended)
```bash
# Read new_metabolic_studies.json and append to studies array in studies.json
# This preserves all existing studies while adding the 7 new ones
```

### Option 2: Manual Addition
Copy each study object from `/sessions/gracious-beautiful-shannon/mnt/LongevityPath/system/new_metabolic_studies.json` into the `studies` array in `/sessions/gracious-beautiful-shannon/mnt/LongevityPath/system/studies.json`

## FAQ Card Implementation

### Update Each Card's Data Structure

For each FAQ card, you need TWO arrays:

#### 1. studyCitations
Contains the **primary** study(ies) cited for that specific card's main claim

#### 2. studyRefs
Contains **all related** studies that support the card's topic

### Card-by-Card Implementation

#### Card: q-score-low
**Question**: "I scored below 25% on metabolic markers — what does this mean?"

**studyCitations**:
```json
["mottillo-2010"]
```

**studyRefs**:
```json
["mottillo-2010"]
```

**Citation Logic**: The Mottillo 2010 meta-analysis directly addresses metabolic syndrome prevalence and mortality risk. With 2-fold increased CVD risk and 1.5-fold increased all-cause mortality, it explains what it means to have poor metabolic health.

---

#### Card: q-score-high
**Question**: "I scored above 75% — what metabolic benefits am I getting?"

**studyCitations**:
```json
["wang-2023-metabolic"]
```

**studyRefs**:
```json
["wang-2023-metabolic", "kramer-2013"]
```

**Citation Logic**:
- Primary (wang-2023): Shows that healthy metabolomic signatures (reflecting optimal metabolic markers) are associated with 17% lower mortality and 25% higher likelihood of reaching longevity (age 85)
- Secondary (kramer-2013): Provides context on metabolic health paradoxes and additional longevity benefits

---

#### Card: q-insulin
**Question**: "Why is fasting insulin the earliest warning sign?"

**studyCitations**:
```json
["balkau-2014", "malmö-2003"]
```

**studyRefs**:
```json
["balkau-2014", "malmö-2003"]
```

**Citation Logic**:
- balkau-2014: Shows fasting insulin in top quartile predicts 3× higher diabetes incidence over 6 years — demonstrating insulin resistance PRECEDES diabetes by years (earliest warning sign)
- malmö-2003: Shows hyperinsulinemia independently predicts 1.58× all-cause mortality (19-year follow-up) — fasting insulin as direct mortality predictor

---

#### Card: q-glucose
**Question**: "What do my fasting glucose numbers really mean?"

**studyCitations**:
```json
["glucose-diabetes-collaboration-2011"]
```

**studyRefs**:
```json
["glucose-diabetes-collaboration-2011"]
```

**Citation Logic**: The DECODE meta-analysis shows that fasting glucose has a linear dose-response relationship with cardiovascular mortality across the ENTIRE glucose spectrum (including "normal" range). This explains why fasting glucose matters even at lower levels.

---

#### Card: q-trig-metabolic
**Question**: "How do triglycerides reflect metabolic health?"

**studyCitations**:
```json
["reaven-1988"]
```

**studyRefs**:
```json
["sarwar-2007", "reaven-1988"]
```

**Citation Logic**:
- Primary (reaven-1988): Seminal paper establishing that elevated triglycerides are part of insulin resistance syndrome; explains the mechanism
- Secondary (sarwar-2007): Quantifies the independent cardiovascular risk from elevated triglycerides (72% higher CHD risk)

---

#### Card: q-hdl-metabolic
**Question**: "Why is HDL important for metabolic health?"

**studyCitations**:
```json
["reaven-1988"]
```

**studyRefs**:
```json
["gordon dj-1989", "reaven-1988"]
```

**Citation Logic**:
- Primary (reaven-1988): Explains HDL as central marker of insulin resistance syndrome; low HDL reflects metabolic dysfunction
- Secondary (gordon-1989): Quantifies benefit of HDL (each 1 mg/dL associated with 2-3% CHD risk reduction)

---

#### Card: q-means-framework
**Question**: "What is Casey Means' 5-marker metabolic health framework?"

**studyCitations**:
```json
["araujo-2019"]
```

**studyRefs**:
```json
["araujo-2019"]
```

**Citation Logic**: The Araújo 2019 study is THE landmark epidemiologic study analyzing exactly these metabolic health markers using NHANES data. It shows only 12.2% of Americans are metabolically healthy, directly supporting Casey Means' framework emphasizing the rarity and importance of true metabolic health.

---

#### Card: q-improve-metabolic
**Question**: "How can I improve my metabolic markers?"

**studyCitations**:
```json
["knowler-2002"]
```

**studyRefs**:
```json
["knowler-2002", "kramer-2013"]
```

**Citation Logic**:
- Primary (knowler-2002): The Diabetes Prevention Program demonstrates that intensive lifestyle intervention reduces diabetes incidence by 58% (NNT=6.9), showing metabolic markers can be improved dramatically through intervention
- Secondary (kramer-2013): Provides additional context that weight management improves metabolic health even in those already metabolically healthy

---

## Data Structure Template

Each card should have this structure:

```json
{
  "card_id": "q-score-low",
  "question": "I scored below 25% on metabolic markers — what does this mean?",
  "studyCitations": [
    "mottillo-2010"
  ],
  "studyRefs": [
    "mottillo-2010"
  ],
  "content": "..."
}
```

## Quality Assurance Checklist

- [ ] All 7 new studies added to studies.json
- [ ] Each study has complete fields: study_id, title, authors, journal, year, DOI, PMID, quality_score, etc.
- [ ] All 8 FAQ cards have studyCitations populated
- [ ] All 8 FAQ cards have studyRefs populated
- [ ] Each studyCitations entry is a non-empty array with at least 1 study_id
- [ ] Each studyRefs entry includes all relevant studies (including those in studyCitations)
- [ ] Study IDs match exactly across files (check spelling, hyphens, case)
- [ ] No circular dependencies or orphaned references
- [ ] Quality scores are justified (13=landmark concept, 12=major meta-analysis, 11=significant study, etc.)
- [ ] All PMIDs and DOIs are valid and verified

## Study Quality Scoring Rationale

### Quality Score 13 (Landmark Concept)
- **reaven-1988**: Seminal paper that defined the modern understanding of metabolic syndrome

### Quality Score 12 (Major Meta-Analysis)
- **mottillo-2010**: 87 studies, 951K participants, clear quantified risks
- **wang-2023-metabolic**: 4 major US prospective cohorts (NHS, HPFS), >100K, 20-28 year follow-up

### Quality Score 11 (High-Quality Study)
- **araujo-2019**: NHANES nationally representative data, contemporary methods
- **kramer-2013**: 8 prospective cohorts, 10+ year follow-up, well-defined outcomes
- **glucose-diabetes-collaboration-2011**: >1 million participants, dose-response analysis

### Quality Score 9-10 (Good Studies)
- **balkau-2014**: Prospective cohort with clear risk stratification (3× RR)
- **malmö-2003**: 19-year follow-up with independent mortality association

### Quality Score 8 (Moderate)
- **karelis-2007**: Small sample but establishes important criteria; limited generalizability

## Files Provided

1. **new_metabolic_studies.json**: All 7 new studies in correct JSON format ready to add to studies.json
2. **metabolic_card_mappings.json**: Pre-formatted studyCitations and studyRefs mappings
3. **METABOLIC_STUDIES_SUMMARY.md**: Comprehensive narrative overview
4. **METABOLIC_STUDIES_TABLE.md**: Detailed reference tables
5. **IMPLEMENTATION_GUIDE.md**: This file

## References by Study ID

### araujo-2019
- PMID: 30484738
- DOI: 10.1089/met.2018.0105
- Journal: Metabolic Syndrome and Related Disorders, 2019;17(1):46-52
- Sample: 16,914 US adults (NHANES 2009-2016)

### mottillo-2010
- PMID: 20863953
- DOI: 10.1016/j.jacc.2010.05.034
- Journal: Journal of the American College of Cardiology, 2010;56(14):1113-1132
- Sample: 951,083 (87 studies)

### kramer-2013
- PMID: 24297192
- DOI: 10.7326/0003-4819-159-11-201312030-00008
- Journal: Annals of Internal Medicine, 2013;159(11):758-769
- Sample: 61,386 (8 studies)

### malmö-2003
- PMID: 12542553
- DOI: 10.1046/j.1365-2796.2003.01077.x
- Journal: Journal of Internal Medicine, 2003;253(2):136-145
- Sample: 6,074 Swedish men, 19-year follow-up

### karelis-2007
- PMID: 17697862
- DOI: 10.1016/j.metabol.2007.03.011
- Journal: Metabolism: Clinical and Experimental, 2007;56(9):1191-1198
- Sample: 38 obese women

### wang-2023-metabolic
- PMID: 36599867
- DOI: 10.1097/MD.0000000000032759
- Journal: Medicine, 2023;102(4):e32759
- Sample: >100,000 (4 cohorts)

### reaven-1988
- PMID: 3056758
- DOI: 10.2337/diab.37.12.1595
- Journal: Diabetes, 1988;37(12):1595-1607
- Sample: Conceptual framework

### glucose-diabetes-collaboration-2011
- PMID: 21443997
- DOI: 10.1007/s00125-011-2144-2
- Journal: Diabetologia, 2011;54(6):1289-1299
- Sample: >1 million (meta-analysis)

## Validation Commands

To verify all studies are properly formatted:
```bash
# Check all study IDs exist and are properly formatted
jq '.[] | .study_id' < new_metabolic_studies.json

# Verify all required fields present
jq '.[] | keys' < new_metabolic_studies.json

# Check for missing PMIDs
jq '.[] | select(.pmid == null) | .study_id' < new_metabolic_studies.json

# Check quality scores range
jq '.[] | .quality_score' < new_metabolic_studies.json | sort -n
```

## Next Steps

1. Copy all study objects from new_metabolic_studies.json into studies.json studies array
2. Update FAQ cards with studyCitations and studyRefs using metabolic_card_mappings.json
3. Verify all study IDs match across files
4. Run quality assurance tests
5. Display FAQ with properly linked studies
