# Citation Verification Checklist

## MANDATORY BEFORE ADDING ANY CITATION

### Step 1: Search & Verify
```
WebSearch: "[Author] [Year] [Key finding] PubMed DOI"
```
- [ ] Found exact paper on PubMed?
- [ ] Title matches expected study?
- [ ] Year matches?

### Step 2: Extract Citation Data
From PubMed/search results, collect:
- [ ] **PubMed ID** (PMID): _______
- [ ] **DOI**: _______
- [ ] **Full Journal Name**: _______
- [ ] **Authors**: _______
- [ ] **Year**: _______
- [ ] **Volume/Issue/Pages**: _______

### Step 3: Verify Link Works
- [ ] Open `https://pubmed.ncbi.nlm.nih.gov/[PMID]/` in browser
- [ ] Confirm title/authors match

### Step 4: Use Standard Format
```html
<div class="study">
    <div class="study-title">[Descriptive Title]</div>
    <div class="study-meta">[Author] et al., [Year] • [Full Journal Name] • doi:[DOI]</div>
    <div class="study-finding"><strong>Key finding:</strong> [Finding text]</div>
    <a href="https://pubmed.ncbi.nlm.nih.gov/[PMID]/" target="_blank" class="study-link">View on PubMed</a>
</div>
```

---

## Common Errors to Avoid

| Error | Prevention |
|-------|------------|
| Wrong PMID | Always search, never guess |
| Abbreviated journal | Use full name (Journal of Nutrition, not J Nutr) |
| Missing DOI | Required for every citation |
| Link not tested | Click it before committing |

---

## Verified Citations Database

### Protein FAQ (protein-evidence.html)

| Study | PMID | DOI | Verified |
|-------|------|-----|----------|
| Moore et al., 2015 | 25056502 | 10.1093/gerona/glu103 | ✅ |
| Mamerow et al., 2014 | 24477298 | 10.3945/jn.113.185280 | ✅ |
| Bauer et al., 2013 | 23867520 | 10.1016/j.jamda.2013.05.021 | ⬜ |
| Naghshi et al., 2020 | 32699048 | 10.1136/bmj.m2412 | ⬜ |
| Devries et al., 2018 | 30383278 | 10.1093/jn/nxy197 | ⬜ |
| Houston et al., 2008 | 18175749 | 10.1093/ajcn/87.1.150 | ⬜ |

---

## AI Instruction

When adding citations, ALWAYS:
1. Search PubMed first to get correct PMID
2. Verify DOI matches the paper
3. Use full journal name
4. Test the link before saving
5. Add to verified database above
