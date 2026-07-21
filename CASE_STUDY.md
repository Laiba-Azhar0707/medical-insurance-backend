# Case Study: Building a Safety Net Against AI Hallucination in a Financial Pipeline

## The setup

This project uses an LLM vision model to read scanned medical documents — prescriptions, pharmacy bills, lab bills, consultation receipts — and extract structured data: medicine names, dosages, prices, quantities. That structured data then feeds a comparison engine that decides how much money to deduct from an insurance claim.

In other words: OCR errors here aren't just annoying, they're *financial* errors. If the model reads a dosage wrong, the system approves or denies money based on a mistake.

## The discovery

While reviewing extraction output during testing, I noticed something concerning: on blurry or low-quality document photos, the model wasn't failing the way I expected. I expected garbled text, missing fields, obvious errors — the normal signature of OCR struggling with a bad image.

Instead, it was returning clean, plausible, complete-looking data. Medicine names that looked real. Dosages in normal ranges. Nothing that visually signaled "I couldn't actually read this."

That's the dangerous failure mode. A model that fails loudly is easy to catch. A model that fails *confidently* is not — and in a pipeline where the output directly drives a financial decision, a confident hallucination is worse than no output at all, because nothing downstream has a reason to question it.

## Why this matters more than the OCR integration itself

It would have been easy to treat "call a vision model, get structured data back" as the finish line. The actual hard problem — the one that doesn't show up in a demo unless you go looking for it — is: **how much should the rest of the system trust this output, and how does it know when not to?**

That question doesn't have a single fix. It needs a layered answer, because no single check catches every version of the failure.

## The fix: three layers, not one

**1. Image quality scoring, before extraction even runs.**
Every uploaded document is checked for blur (via Laplacian variance on the grayscale image) and minimum resolution before it's sent to the model at all. Obviously unreadable documents get caught here, cheaply, without spending an API call on data that was never going to be trustworthy.

**2. Confidence signals attached to every extracted item, not just a final pass/fail.**
Rather than a single "did this work" boolean, the extraction pipeline tracks an illegibility ratio and a blank-field ratio per document. This turns "trust or don't trust" into a spectrum the rest of the system can reason about — a document that's 90% clear but has one unreadable line is a very different case from one that's mostly illegible, and they should be handled differently.

**3. Automatic review-flagging when confidence drops below threshold.**
This is the layer that actually closes the loop. When a claim's confidence signals fall below threshold, it doesn't get auto-processed — it gets routed for human review instead. The system is explicitly allowed to say "I don't know" and hand off, rather than silently converting uncertainty into a financial decision.

## What I'd tell another engineer building something similar

The tempting version of this system stops at "OCR extraction working." The version that's actually safe to put in front of real money has to assume the model will occasionally be wrong in the most convincing possible way, and needs a design that doesn't depend on catching that by eye.

If I were extending this further, the next layer would be surfacing *why* something was flagged directly in the reviewer's UI — not just that it needs review, but which specific field triggered it and what the confidence signal looked like — so a human reviewer isn't starting from zero either.

---

*Part of the [AI-Powered Medical Insurance Claims Processing](README.md) project.*