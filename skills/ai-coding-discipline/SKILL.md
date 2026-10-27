---
name: ai-coding-discipline
description: >
  Mandatory coding discipline rules that prevent common AI coding anti-patterns.
  MUST be loaded for ALL code writing, editing, reviewing, bug fixing, and testing tasks.
  Trigger on: writing code, editing code, fixing bugs, writing tests, implementing features,
  refactoring, code review, creating functions, adding error handling, debugging.
  This skill enforces fail-fast principles, proper error propagation, meaningful tests,
  and disciplined debugging workflows. Always active when Claude writes or modifies code.
---

# AI Coding Discipline

> These rules override default AI coding tendencies. Follow them in ALL code you write or modify.

---

## Rule 1: No Silent Fallbacks

**Never use fallback values to mask data that should not be missing.**

```typescript
// FORBIDDEN — hides upstream bugs
const price = product?.price ?? 0;
const userName = user?.name || "Unknown";

// CORRECT — fail fast when data contract is violated
if (product.price == null) {
  throw new Error(`Product ${product.id} is missing price`);
}
const price = product.price;
```

**When fallbacks ARE acceptable:**
- User-facing display with explicit design intent (e.g., avatar placeholder)
- Optional configuration with documented defaults
- External input parsing where absence is a valid state

**Checklist before writing `??`, `||`, or `?.`:**
1. Can this value legitimately be null/undefined at this point?
2. If it is null, will the fallback produce a correct result downstream?
3. Would a thrown error help me find a bug faster?

If the answer to #3 is yes, throw instead of falling back.

---

## Rule 2: No Catch-All try/catch in Business Logic

**Business logic functions must NOT wrap everything in try/catch. Let errors propagate naturally.**

```typescript
// FORBIDDEN — swallows all errors into a useless null
async function createOrder(data: OrderInput) {
  try {
    const user = await getUser(data.userId);
    const coupon = await validateCoupon(data.couponCode);
    const order = await saveOrder({ ...data, discount: coupon.value });
    return order;
  } catch (error) {
    console.log('Error creating order:', error);
    return null; // caller gets null, has no idea what failed
  }
}

// CORRECT — let errors bubble up, catch at the boundary
async function createOrder(data: OrderInput) {
  const user = await getUser(data.userId);
  const coupon = await validateCoupon(data.couponCode);
  const order = await saveOrder({ ...data, discount: coupon.value });
  return order;
}

// Catch ONLY at the API/controller boundary
app.post('/orders', async (req, res) => {
  try {
    const order = await createOrder(req.body);
    res.json(order);
  } catch (error) {
    logger.error('Order creation failed', { error, body: req.body });
    res.status(500).json({ error: 'Order creation failed' });
  }
});
```

**Where try/catch IS appropriate:**
- API route handlers / controller boundaries
- Top-level event handlers (message queues, cron jobs)
- Operations where partial failure is expected and recovery is defined (e.g., batch processing with per-item error handling)
- Specific, named error types you intend to handle differently

**Never catch `Error` just to return `null`, `undefined`, `false`, or an empty object.**

---

## Rule 3: Tests Must Fail When Code Breaks

**Every test must verify specific business outcomes. A test that passes when the core logic is deleted is worthless.**

```typescript
// FORBIDDEN — passes even if processOrder returns garbage
test('should process order', async () => {
  const result = await processOrder(mockOrder);
  expect(result).toBeDefined();
});

// CORRECT — verifies exact business behavior
test('should calculate total with 10% discount', async () => {
  const result = await processOrder({
    ...mockOrder,
    discount: 0.1,
  });
  expect(result.totalAmount).toBe(900);       // 1000 * 0.9
  expect(result.discountAmount).toBe(100);
  expect(result.status).toBe('confirmed');
});
```

**Test quality checklist:**
1. If I delete the function body, does this test fail? If not, the test is useless.
2. Am I testing behavior or just testing that "something exists"?
3. Do my assertions check concrete values, not just truthiness?

**Banned weak assertions** (unless testing existence is the actual requirement):
- `toBeDefined()`, `toBeTruthy()`, `toBeFalsy()` as sole assertion
- `toHaveLength(expect.any(Number))`
- `expect(result).not.toBeNull()` without further value checks

---

## Rule 4: No Hardcoded Lookup-Table Implementations

**Never implement business logic by hardcoding return values that match test cases.**

```typescript
// FORBIDDEN — fake implementation that "fits" the tests
function calculateDiscount(amount: number, level: string): number {
  if (amount === 1000 && level === 'gold') return 100;
  if (amount === 500 && level === 'silver') return 25;
  return 0;
}

// CORRECT — real logic
function calculateDiscount(amount: number, level: string): number {
  const rates: Record<string, number> = { gold: 0.1, silver: 0.05, bronze: 0.02 };
  const rate = rates[level] ?? 0;
  return amount * rate;
}
```

**How to prevent this:**
- Use diverse test data: multiple amounts, edge cases, boundary values
- Add property-based / fuzzy tests where appropriate
- Test with values NOT in the original spec to catch lookup-table fakes

---

## Rule 5: Red-Green Testing (TDD Order)

**When fixing a bug, always write the failing test FIRST, then fix the code.**

```
Correct order:
1. Discover bug
2. Write a test that reproduces the bug
3. Run the test — confirm it FAILS (red)
4. Fix the code
5. Run the test — confirm it PASSES (green)
```

**Why this matters:** If you fix the code first and then write a test, you can never be sure the test would have caught the bug. The test might pass for the wrong reason.

**Never skip step 3.** Seeing the test go from red to green is the proof that the test is valid.

---

## Rule 6: Never Remove Debug Logs During a Fix

**When debugging, debug logs are removed ONLY after the human confirms the fix works.**

```
FORBIDDEN workflow:
1. Human asks to add debug logs
2. AI adds logs
3. Human runs code, shares log output
4. AI "finds the problem", applies fix AND removes debug logs in the same edit
5. Fix doesn't work — logs are gone, must re-add them

CORRECT workflow:
1. Human asks to add debug logs
2. AI adds logs
3. Human runs code, shares log output
4. AI applies fix ONLY — debug logs stay untouched
5. Human verifies the fix
6. Human decides when to remove debug logs (or asks AI to remove them)
```

**Rule: Never touch debug/diagnostic logs in the same commit as a fix. They are separate concerns.**

---

## Quick Reference: Self-Check Before Submitting Code

Before finalizing any code change, run through this checklist:

| Check | Question |
|-------|----------|
| Fallbacks | Did I use `??` or `\|\|` to hide a value that should never be missing? |
| Error handling | Did I add try/catch in business logic that should just let errors propagate? |
| Test strength | Would my tests still pass if I deleted the implementation? |
| Test honesty | Did I hardcode values to match test cases instead of implementing real logic? |
| TDD order | For bug fixes: did I see the test fail before applying the fix? |
| Debug logs | Am I removing diagnostic logs in the same change as the fix? |

If any answer is "yes", revise before proceeding.
