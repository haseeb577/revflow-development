# Google Doc Template Example
## Copy this content into your Google Doc for testing

---

# Welcome to [BUSINESS_NAME]

We are [CITY]'s premier [NICHE] company, serving the community with excellence for over [YEARS_EXPERIENCE] years.

## Contact Us

📞 **Call us:** [PHONE_LINK]

✉️ **Email:** [EMAIL]

📍 **Address:** [ADDRESS]

---

## Our Services

[SERVICES_LIST]

---

## Why Choose [BUSINESS_NAME]?

- ✓ Licensed & Insured
- ✓ [YEARS_EXPERIENCE]+ Years of Experience
- ✓ Local Experts in [CITY], [STATE]
- ✓ Professional & Reliable Service

[IF emergency_available=yes]
## 🚨 24/7 Emergency Service Available

**Need immediate help?** Call us anytime for emergency [NICHE] services in [CITY]!

We're available 24 hours a day, 7 days a week to help when you need us most.
[/IF]

---

## Service Area

We proudly serve [CITY], [STATE] and all surrounding areas. Our team is committed to providing top-quality [NICHE] services to every customer.

---

## Get Started Today

Ready to experience the [BUSINESS_NAME] difference? Contact us today for a free consultation!

**Call:** [PHONE_LINK]  
**Email:** [EMAIL]

---

*Serving [CITY], [STATE] since [YEARS_EXPERIENCE] years ago*

---

## Instructions:

1. Copy the content above
2. Paste into a new Google Doc
3. Replace merge fields like `[BUSINESS_NAME]`, `[CITY]`, etc. with your actual merge field placeholders
4. Set document to "Anyone with the link can VIEW"
5. Copy the document URL
6. Extract the document ID from the URL
7. Use in your CSV file's `page_content_doc_url` column

## Merge Fields Used:

- `[BUSINESS_NAME]` - Business name from CSV
- `[CITY]` - City from CSV
- `[STATE]` - State from CSV
- `[NICHE]` - Service niche from CSV
- `[PHONE]` - Phone number (formatted)
- `[PHONE_LINK]` - Clickable phone link
- `[EMAIL]` - Email address (clickable link)
- `[ADDRESS]` - Full address
- `[YEARS_EXPERIENCE]` - Years in business
- `[SERVICES_LIST]` - HTML list from `services_offered` field
- `[IF emergency_available=yes]...[/IF]` - Conditional content

