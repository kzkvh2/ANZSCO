# Email Nurture — Setup Guide

## What you need to do first
1. Sign up at https://brevo.com (free — 300 emails/day)
2. Go to Settings → SMTP & API → Generate API Key
3. Verify your sending email (Settings → Senders & IP)
4. Share the API key so the landing page can be updated

## The 2-email sequence (content ready)

### Email 1 — Immediate (sent on signup)

**Subject:** Your ANZSCO Code Finder access

> Hi [name],
>
> Thanks for signing up.
>
> You can use the tool right now — no waiting list:
> **https://kzkvh2-anzsco.hf.space**
>
> Upload your CV (PDF or Word) and you'll get your top 5 ANZSCO code matches in about 10 seconds.
>
> A few things to know:
> - The tool works best with a text-based CV (not a scanned PDF)
> - It returns matches with explanations — use the #1 result as your starting point
> - Always verify against the [Home Affairs skilled occupation list](https://immi.homeaffairs.gov.au/visas/working-in-australia/skill-occupation-list) before lodging
>
> If the results don't look right, reply to this email and I'll take a look.
>
> — Peter
> ANZSCO Code Finder

---

### Email 2 — Day 5 (follow-up)

**Subject:** 3 mistakes people make choosing their ANZSCO code

> Hi [name],
>
> Quick follow-up — in case you haven't tried the tool yet, or if you want to double-check your result.
>
> **The 3 most common ANZSCO mistakes:**
>
> **1. Choosing by job title, not by duties**
> ANZSCO codes are classified by what you actually do, not what your employer calls you. A "Digital Marketing Specialist" might be a Marketing Specialist (225113) or an Advertising Manager (131011) depending on whether they manage a team or execute campaigns.
>
> **2. Ignoring the skill level**
> Each ANZSCO code has a skill level (1–5). Skill Level 1 occupations require a degree. If you're applying under a points-tested visa, your skills assessment authority will check that your experience matches the level.
>
> **3. Picking the most senior-sounding code**
> If you've managed a team but spent 80% of your time doing technical work, you're more likely a technical specialist than a manager. The code should reflect where most of your duties fall.
>
> The tool at https://kzkvh2-anzsco.hf.space accounts for all of this — it reads your full CV, not just your job title.
>
> If you've already got your result and want a second opinion, just reply.
>
> — Peter

---

## Landing page integration (when you have Brevo API key)

Replace the Web3Forms action in `docs/index.html` with this approach:
1. Keep Web3Forms for the email capture (it still sends you the notification)
2. Add a secondary POST to Brevo's Contacts API to add the subscriber

The integration code (add your API key to replace `BREVO_API_KEY_HERE`):

```javascript
async function addToBrevo(email, name) {
  await fetch('https://api.brevo.com/v3/contacts', {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'content-type': 'application/json',
      'api-key': 'BREVO_API_KEY_HERE',
    },
    body: JSON.stringify({
      email: email,
      attributes: { FIRSTNAME: name || '' },
      listIds: [2],        // replace 2 with your actual Brevo list ID
      updateEnabled: true,
    }),
  });
}
```

Add `addToBrevo(email, name)` call inside the form's success handler (after Web3Forms confirms).

The automation in Brevo:
- Trigger: Contact added to list [your list]
- Step 1: Send Email 1 immediately
- Step 2: Wait 5 days
- Step 3: Send Email 2
