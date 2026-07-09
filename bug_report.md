# The CoWork API Bug Report (Our Journey!)

Hey there! 👋 This is our complete log of all the bugs we found and squashed while fixing the CoWork API. We've tackled these in phases, starting from the security nightmares all the way to the tricky race conditions. Here is the full story of what went wrong and how we fixed it!

---

## Phase 1: Authentication, Permissions & Security

### 1. The Token Revocation Nightmare
- **Where it happened:** `app/auth.py`, Line 97
- **The problem:** When someone logged out, the code accidentally blacklisted their entire User ID instead of just the specific token they were using! 
- **The chaos:** If you logged out on your phone, you instantly got kicked out of your desktop session too. Oops!
- **Our fix:** We changed the logic to look for the token's unique ID (`jti`) instead of the user's ID (`sub`). Problem solved!

### 2. The Duplicate Username Glitch
- **Where it happened:** `app/routers/auth.py`, Lines 32-43
- **The problem:** If you tried to register a username that already existed, the API just happily returned a `200 OK` and handed you the existing user's data. 
- **The chaos:** Massive security flaw! Attackers could figure out who was registered, and it broke the `409 USERNAME_TAKEN` rule.
- **Our fix:** We added a quick check to throw a proper `409` error if the username is already taken.

### 3. The Infinite Refresh Token Exploit
- **Where it happened:** `app/routers/auth.py`, Lines 81-85
- **The problem:** When you used a refresh token to get a new access token, the system never threw the old refresh token away.
- **The chaos:** A hacker could steal a refresh token and use it forever.
- **Our fix:** We added logic to instantly blacklist refresh tokens as soon as they are used. 

### 4. The Peeping Tom Bug (Privacy Leak)
- **Where it happened:** `app/routers/bookings.py`, Lines 156-163
- **The problem:** The `get_booking` endpoint forgot to check if the person asking for the booking actually owned it.
- **The chaos:** Any regular member could snoop on the private bookings of any other member in their organization. 
- **Our fix:** We added a strict ownership check. If you aren't the owner (or an admin), you get a `404`!

### 5. The Cross-Organization Data Heist
- **Where it happened:** `app/services/export.py` & `app/routers/admin.py`
- **The problem:** Admins could pass any `room_id` into the export tool, and the API would just hand over all the bookings for that room without checking who owned it.
- **The chaos:** Admin A could literally download Admin B's financial data. Yikes!
- **Our fix:** We added a validation step to ensure the `room_id` actually belongs to the admin's organization before exporting anything.

---

## Phase 2: Booking Math & Logic

### 6. The Timezone Amnesia
- **Where it happened:** `app/timeutils.py`, Line 13
- **The problem:** The app stripped timezones off dates without actually converting them to UTC first.
- **The chaos:** If you booked a room at 3 PM in New York, the server thought you meant 3 PM in London. All the time math was completely broken.
- **Our fix:** We forced the datetimes to convert to UTC (`.astimezone(timezone.utc)`) before stripping the timezone tags.

### 7. The Back-to-Back Booking Block
- **Where it happened:** `app/routers/bookings.py`, Lines 50-51
- **The problem:** The conflict checker used a `<=` operator. 
- **The chaos:** If Alice booked a room until 3:00 PM, Bob couldn't book it starting at 3:00 PM. The system thought they overlapped by zero seconds!
- **Our fix:** Swapped `<=` for `<`. Now back-to-back bookings work beautifully.

### 8. The Math Fail (Refunds & Rounding)
- **Where it happened:** `app/routers/bookings.py` & `app/services/refunds.py`
- **The problem:** The app used floating-point math and Python's weird `round()` function (which rounds halves to even numbers). Also, canceling with less than 24 hours' notice accidentally gave a 50% refund!
- **The chaos:** Users got slightly incorrect refund amounts, and last-minute cancellations were too generous.
- **Our fix:** We rewrote the math using strict integers `(price * percent + 50) // 100` and fixed the logic to give a 0% refund for late cancellations.

### 9. The Messy Pagination
- **Where it happened:** `app/routers/bookings.py`, Lines 137-139
- **The problem:** The bookings list sorted backwards, skipped the first page completely, and ignored the `limit` parameter.
- **The chaos:** Users couldn't see their earliest bookings, and the pages were totally chaotic.
- **Our fix:** We fixed the offset math `(page - 1) * limit`, set the sort order to ascending, and actually used the `limit` variable!

---

## Phase 3: Caching Updates

### 10. The Stale Cache Bug
- **Where it happened:** `app/routers/bookings.py`
- **The problem:** Creating a booking forgot to update the admin usage reports, and canceling a booking forgot to update room availability.
- **The chaos:** Dashboards showed out-of-date information for hours!
- **Our fix:** We added the missing `cache.invalidate` calls so everything stays perfectly synced in real-time.

---

## Phase 4: Concurrency & The Final Polish

### 11. The Double Refund Race Condition
- **Where it happened:** `app/routers/bookings.py`
- **The problem:** If you clicked "Cancel" twice really fast, both clicks would pass the initial checks and give you two refunds for the same booking.
- **Our fix:** We used an atomic SQL update (`update({"status": "cancelled"})`) so the database acts as the ultimate source of truth, preventing double cancellations.

### 12. Rate Limiting Memory Leaks
- **Where it happened:** `app/services/ratelimit.py`
- **The problem:** The rate limiter didn't use thread locks, meaning heavy traffic would overwrite the logs and let hackers bypass the limits.
- **Our fix:** Added a `threading.Lock()` to keep things orderly.

### 13. The Deadlocking Emails
- **Where it happened:** `app/services/notifications.py`
- **The problem:** Creating and canceling bookings grabbed two different locks in the opposite order (`email` then `audit`, versus `audit` then `email`).
- **The chaos:** If two users did this at the exact same time, the server would deadlock and freeze forever!
- **Our fix:** Un-nested the locks so they trigger one after the other safely.

### 14. The Global Booking Chaos
- **Where it happened:** `app/routers/bookings.py`
- **The problem:** If you spammed the "Book" button, you could bypass your 3-booking quota and double-book the same room.
- **Our fix:** Put a massive `_booking_lock` around the entire creation process to ensure requests queue up politely.

### 15. The Amnesiac Counters (Reference Codes & Stats)
- **Where it happened:** `app/services/reference.py` and `app/services/stats.py`
- **The problem:** Reference codes and live room stats reset to zero every time the server restarted!
- **Our fix:** Wired them up to a database session so they initialize themselves from actual historical data on startup. 

### 16. The Generous Grace Window
- **Where it happened:** `app/routers/bookings.py`
- **The problem:** You could technically book a room up to 5 minutes in the past!
- **Our fix:** Changed the math to strictly enforce `start <= now`. No more time travel!

### 17. The 0-Hour Booking Trick
- **Where it happened:** `app/routers/bookings.py`
- **The problem:** The app forgot to check for a minimum duration.
- **Our fix:** Added a strict `MIN_DURATION_HOURS` check so you have to book a room for at least 1 hour.

### 18. The Token Expiry Typo
- **Where it happened:** `app/auth.py`
- **The problem:** Access tokens were supposed to expire in 15 minutes, but a stray `* 60` multiplier meant they lasted 15 hours!
- **Our fix:** Deleted the multiplier. 

### 19. The Details View Typo
- **Where it happened:** `app/routers/bookings.py`
- **The problem:** When viewing a booking's details, a rogue line of code replaced the `start_time` with the `created_at` timestamp.
- **Our fix:** Deleted the bad line so the start time actually shows the start time!

---
*Whew! We found them, we fixed them, and the API is finally ready for the real world!* 🚀
