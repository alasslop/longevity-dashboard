# LongevityPath — Evidence Map Reference

> Claim tag vocabulary and summary index for the evidence database.
> Full data lives in `longevitypath.db` — query with `registry.py` (see ARCHITECTURE.md §3.7).

---

## Claim Tag Vocabulary

Tags use the format `exposure→outcome`. Reuse existing tags; add new ones only when no tag fits.

| Tag | Meaning |
|-----|---------|
| `sleep-duration→mortality` | Sleep length and all-cause death risk |
| `sleep-duration→CVD` | Sleep length and cardiovascular disease |
| `sleep-duration→confounding` | Confounders in sleep-duration associations |
| `sleep-regularity→mortality` | Consistent sleep timing and death risk |
| `sleep-quality→health` | Subjective/objective sleep quality and health |
| `insomnia→mortality` | Insomnia symptoms and death risk |
| `long-sleep→health` | Oversleeping and adverse outcomes |
| `social-jet-lag→obesity` | Weekend-weekday sleep mismatch and weight |
| `catch-up-sleep→mortality` | Weekend catch-up sleep and death risk |
| `wearable→sleep-accuracy` | Consumer device validation for sleep |
| `caffeine→sleep` | Caffeine timing/dose and sleep quality |
| `temperature→sleep` | Room/body temperature and sleep quality |
| `light-therapy→sleep` | Light exposure and sleep outcomes |
| `warm-bath→sleep` | Pre-bed warming and sleep onset |
| `CBT-I→insomnia` | Cognitive behavioral therapy for insomnia |
| `magnesium→sleep` | Magnesium supplementation and sleep |
| `ashwagandha→sleep` | Ashwagandha and sleep outcomes |
| `glycine→sleep` | Glycine and sleep quality |
| `melatonin→sleep-onset` | Melatonin dose/timing and sleep onset |
| `sleep-debt→cognition` | Cumulative sleep loss and cognitive performance |
| `motivation→behavior-change` | Motivational interviewing and health behavior |
| `grit→physical-activity` | Perseverance and exercise adherence |
| `locus-of-control→prevention` | Health locus of control and preventive behavior |
| `growth-mindset→health` | Growth mindset and health outcomes |
| `mHealth→behavior-change` | Mobile health apps and behavior change |
| `habit→maintenance` | Habit formation and behavior maintenance |
| `positive-affect→mortality` | Positive emotions and death risk |
| `flow→wellbeing` | Flow states and health/wellbeing |
| `social-connection→mortality` | Social isolation/connection and death risk |
| `social-connection→confounding` | Confounders in social-isolation findings |
| `purpose→mortality` | Purpose/meaning in life and death risk |
| `goal-pursuit→wellbeing` | Goal-directed behavior and wellbeing |
| `stress-mindset→health` | Stress perception and health outcomes |
| `emotion-regulation→CVD` | Emotion regulation and cardiovascular health |
| `meditation→wellbeing` | Meditation/mindfulness and psychological health |
| `meditation→adverse-effects` | Meditation harms and adverse outcomes |
| `nature→wellbeing` | Nature exposure and wellbeing |
| `gratitude→wellbeing` | Gratitude practice and wellbeing |
| `diet-quality→mortality` | Overall dietary quality and death risk |
| `fruit-veg→mortality` | Fruit/vegetable intake and death risk |
| `UPF→health` | Ultra-processed food and health outcomes |
| `mediterranean→CVD` | Mediterranean diet and cardiovascular disease |
| `saturated-fat→health` | Saturated fat and health outcomes |
| `sodium→health` | Sodium intake and health burden |
| `alcohol→mortality` | Alcohol dose-response and death risk |
| `alcohol→confounding` | Methodological bias in alcohol-mortality studies |
| `centenarian-diet→longevity` | Dietary patterns in long-lived populations |
| `flexible-dieting→adherence` | Flexible vs rigid eating and adherence |
| `eating-speed→metabolic` | Eating rate and metabolic outcomes |
| `food-tracking→weight` | Food logging and weight management |
| `meal-timing→metabolic` | Meal timing and metabolic health |
| `protein→mortality` | Protein intake and all-cause death risk |
| `protein→cancer` | Protein intake and cancer mortality risk |
| `protein→muscle` | Protein and muscle mass/strength |
| `protein→sarcopenia` | Protein and sarcopenia prevention |
| `protein-source→mortality` | Animal vs plant protein and death risk |
| `protein-dose→MPS` | Per-meal protein dose and muscle protein synthesis |
| `protein-distribution→MPS` | Even protein spacing and synthesis |
| `protein-deficit→muscle` | High protein during calorie deficit and muscle preservation |
| `protein-timing→muscle` | Protein timing (peri-workout) and muscle outcomes |
| `protein-source→muscle` | Plant vs animal protein and muscle outcomes |
| `amino-acids→quality` | Amino acid profiles by protein source |
| `CRF→mortality` | Cardiorespiratory fitness and death risk |
| `HIIT→VO2max` | High-intensity interval training and VO2max gains |
| `exercise-dose→health` | Exercise volume and health outcomes |
| `PA→health` | Physical activity and health outcomes (umbrella) |
| `VO2max-estimation→accuracy` | Field test estimation accuracy |
| `muscle-strength→mortality` | Grip/overall strength and death risk |
| `resistance-training→aging` | Resistance exercise and aging outcomes |
| `push-ups→CVD` | Push-up capacity and cardiovascular risk |
| `chair-stand→function` | Chair stand norms and functional capacity |
| `PERMA→validation` | PERMA-Profiler psychometric validation |

---

## Claim Summary Index

At-a-glance evidence balance. `+` = supporting, `−` = contradicting, `±` = conditional/mixed. Auto-generated by `python registry.py export-summary`.

| Claim | #+ | #− | #± | Best+ | Best− | Net | Confidence | Gap? |
|-------|----|----|-----|-------|-------|-----|------------|------|
| `sleep-duration→mortality` | 1 | 0 | 0 | Ungvari 2025 (12) | — | + | Strong | Need contradicting study |
| `sleep-duration→CVD` | 1 | 0 | 0 | Huang 2022 (11) | — | + | Moderate | Need contradicting study |
| `sleep-regularity→mortality` | 1 | 0 | 0 | Windred 2024 (12) | — | + | Strong | Need contradicting study |
| `sleep-quality→health` | 2 | 0 | 0 | Ge 2019 (12) | — | + | Strong | Need contradicting study |
| `insomnia→mortality` | 1 | 0 | 0 | Ge 2019 (12) | — | + | Strong | Need contradicting study |
| `sleep-duration→confounding` | 0 | 0 | 1 | — | — | ± | — | Challenges causal interpretation |
| `long-sleep→health` | 1 | 0 | 0 | Jike 2018 (12) | — | + | Strong | — |
| `social-jet-lag→obesity` | 1 | 0 | 0 | Arab 2024 (10) | — | + | Moderate | Need contradicting study |
| `catch-up-sleep→mortality` | 0 | 1 | 0 | — | Chaput 2024 (9) | − | Moderate | Contradicts catch-up benefit |
| `wearable→sleep-accuracy` | 2 | 0 | 0 | Schyvens 2025 (8) | — | + | Moderate | — |
| `caffeine→sleep` | 1 | 0 | 0 | Gardiner 2023 (10) | — | + | Moderate | — |
| `magnesium→sleep` | 2 | 0 | 0 | Mah & Pitre 2021 (8) | — | + | Moderate | Small samples |
| `ashwagandha→sleep` | 2 | 0 | 0 | Fatima 2024 (9) | — | + | Moderate | — |
| `melatonin→sleep-onset` | 1 | 0 | 0 | Cruz-Sanabria 2024 (10) | — | + | Moderate | — |
| `sleep-debt→cognition` | 1 | 0 | 0 | Van Dongen 2003 (10) | — | + | Landmark | — |
| `motivation→behavior-change` | 1 | 0 | 0 | Krebs 2018 (11) | — | + | Strong | — |
| `grit→physical-activity` | 1 | 0 | 0 | Singh 2024 (9) | — | + | Moderate | — |
| `locus-of-control→prevention` | 2 | 0 | 0 | Cheng 2016 (11) | — | + | Strong | — |
| `growth-mindset→health` | 1 | 0 | 0 | Burnette 2023 (12) | — | + | Strong | — |
| `positive-affect→mortality` | 1 | 0 | 0 | Chida & Steptoe 2008 (11) | — | + | Landmark | — |
| `flow→wellbeing` | 1 | 0 | 0 | Peifer 2022 (9) | — | + | Moderate | — |
| `social-connection→mortality` | 2 | 0 | 1 | Holt-Lunstad 2015 (12) | — | + | Strong (but confounding concerns) | See ± entry |
| `purpose→mortality` | 2 | 0 | 0 | Cohen 2016 (10) | — | + | Strong | — |
| `goal-pursuit→wellbeing` | 2 | 0 | 0 | Klug & Maier 2015 (10) | — | + | Moderate | — |
| `stress-mindset→health` | 1 | 0 | 0 | Keller 2012 (10) | — | + | Moderate | — |
| `emotion-regulation→CVD` | 1 | 0 | 0 | Panaite 2015 (10) | — | + | Moderate | — |
| `meditation→wellbeing` | 2 | 0 | 0 | Goyal 2014 (12) | — | + | Strong | — |
| `meditation→adverse-effects` | 0 | 2 | 0 | — | Van Dam 2025 (9) | − | Moderate | Harms underreported |
| `nature→wellbeing` | 2 | 0 | 0 | Choi 2025 (12) | — | + | Strong | — |
| `diet-quality→mortality` | 2 | 0 | 0 | GBD 2018 (12) | — | + | Strong | — |
| `fruit-veg→mortality` | 1 | 0 | 0 | Aune 2017 (12) | — | + | Strong | — |
| `UPF→health` | 2 | 0 | 0 | Lane 2024 (12) | — | + | Strong | — |
| `mediterranean→CVD` | 1 | 0 | 0 | Estruch 2018 (12) | — | + | Landmark | — |
| `saturated-fat→health` | 2 | 1 | 0 | de Souza 2015 (11) | Dehghan 2017 (10) | + (contested) | Debated | Active scientific dispute |
| `alcohol→mortality` | 1 | 0 | 0 | Wood 2018 (12) | — | + | Strong | — |
| `alcohol→confounding` | 0 | 0 | 2 | — | — | ± | — | J-curve likely artifact |
| `protein→mortality` | 1 | 0 | 1 | Naghshi 2020 (12) | — | + (source-dependent) | Strong for plant | See ± |
| `protein→cancer` | 0 | 1 | 1 | — | Levine 2014 (9) | − (age-dependent) | Moderate | Age <65 risk; >65 protective |
| `protein-source→mortality` | 0 | 0 | 1 | — | — | ± | — | Animal ↑ risk, plant ↓ risk |
| `protein→muscle` | 2 | 0 | 0 | Devries 2018 (11) | — | + | Strong | — |
| `protein→sarcopenia` | 2 | 0 | 0 | Han 2024 (10) | — | + | Strong | — |
| `CRF→mortality` | 2 | 0 | 0 | Mandsager 2018 (12) | — | + | Strong | — |
| `muscle-strength→mortality` | 1 | 0 | 0 | Garcia-Hermoso 2018 (12) | — | + | Strong | — |
| `resistance-training→aging` | 2 | 0 | 0 | Peterson 2010 (10) | — | + | Strong + Landmark | — |
