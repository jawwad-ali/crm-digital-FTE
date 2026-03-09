# Manual Testing — Web Support Form

## Prerequisites

### 1. Start Redis

```bash
# From Windows (WSL)
wsl sudo service redis-server start

# Verify Redis is running
wsl redis-cli ping
# Expected output: PONG
```

> **Note:** Redis is required for the async background task flow (job polling). Without Redis, the backend falls back to synchronous mode automatically.

### 2. Start the Backend (FastAPI)

```bash
cd D:\crm-digital-FTE
.venv\Scripts\activate
uvicorn api.main:app --reload
```

Backend runs at `http://localhost:8000`. Verify with `GET http://localhost:8000/health`.

### 3. Start the Frontend (Next.js)

```bash
cd D:\crm-digital-FTE\web
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## Test Scenarios

### 1. Basic Submit + Response

1. Open `http://localhost:3000`
2. Fill in the form:
   - **Name:** `Ali jawwad`
   - **Email:** `ali.jawwad@example.com`
   - **Message:** `Hi, I can't log into my account. I've tried my password multiple times and now it seems locked. What should I do?`
3. Click **Send Message**
4. Verify: a processing indicator (pulsing dots) appears
5. Verify: the AI agent response appears in the chat thread as a left-aligned message
6. Verify: the health status shows a green "Connected" dot

### 2. Multi-turn Conversation

1. Complete Test 1 (submit and receive a response)
2. Verify: the name/email form collapses into a compact header bar (e.g., "Ali jawwad (ali.jawwad@example.com)")
3. Verify: a message-only textarea input appears
4. Type a follow-up message and send it:
   - `Thanks! I'm now logged in. How do I enable two-factor authentication on my account?`
5. Verify: both the original exchange and the follow-up exchange are visible in the chat thread
6. Send a third message and verify all three exchanges are visible:
   - `One more thing — how can I change my notification preferences? I'm getting too many emails.`

### 3. Validation

1. Open `http://localhost:3000`
2. Click **Send Message** without filling any fields
3. Verify: inline error messages appear below each required field
4. Enter an invalid email and submit:
   - **Name:** `Sara`
   - **Email:** `sara-at-mail`
   - **Message:** `Test`
5. Verify: an email format error appears
6. Fix the email to `sara@mail.com`, then paste a long message approaching 2000 characters:
   ```
   I'm having trouble getting started with the platform and I need some help. I signed up last week using my work email and completed the onboarding wizard. I created my first project and invited three team members. However, I'm running into several issues. First, the task board columns don't seem to update when I drag and drop tasks between them. I've tried refreshing the page and clearing my browser cache but the problem persists. Second, I set up the Slack integration yesterday but notifications are not coming through to our Slack channel. I followed all the steps in the integration setup and authorized the connection. Third, I'm trying to use the API to automate some of our workflows but I'm getting rate limit errors even though I'm on the Pro plan which should allow 100 requests per minute. I've double checked my API key and it seems valid. I've also tried generating a new key but the issue continues. Additionally, I noticed that the export feature is not including attachments when I export in CSV format. I need the attachments for our compliance records. Could you also let me know how to set up webhooks for task creation events? I want to trigger an external workflow whenever a new task is created in our main project. Finally, I'd like to understand the security measures in place for our data. We handle sensitive customer information and need to ensure we meet SOC 2 compliance requirements. Please provide detailed guidance on each of these issues. Thank you for your help and I look forward to resolving these problems quickly.
   ```
7. Verify: the character counter turns **amber** at 90% (1800+ chars)
8. Keep typing past 2000 characters
9. Verify: the counter turns **red** and the submit button is disabled

### 4. Error Recovery

1. Stop the backend server (`Ctrl+C` in the backend terminal)
2. Fill in the form:
   - **Name:** `Omar Raza`
   - **Email:** `omar.raza@example.com`
   - **Message:** `How do I export all my project data? I need everything in JSON format for an audit.`
3. Click **Send Message**
4. Verify: an error banner appears with a **Try Again** button
5. Restart the backend server
6. Click **Try Again**
7. Verify: the original data is resubmitted (no need to re-enter name/email/message)
8. Verify: the response appears after retry

### 5. Embed Mode

1. Open `http://localhost:3000/embed`
2. Verify: the support form renders **without** a page heading, header, or footer
3. Open `http://localhost:3000/embed-example.html`
4. Verify: the form loads inside the iframe and is fully functional
5. Submit a message through the iframe:
   - **Name:** `Fatima Noor`
   - **Email:** `fatima.noor@example.com`
   - **Message:** `How do I reset my account password? I've tried the forgot password link but I'm not receiving the reset email.`
6. Verify: the response comes back inside the iframe

### 6. Mobile Responsiveness

1. Open `http://localhost:3000`
2. Open browser DevTools and toggle the device toolbar (or resize the window)
3. Set viewport to **320px** width
4. Verify: single-column layout, no horizontal scrollbar
5. Verify: all input fields and buttons have adequate touch target size (at least 44px height)
6. Set viewport to **768px** (tablet) and **1920px** (desktop)
7. Verify: layout adjusts appropriately at each breakpoint

### 7. Keyboard Navigation

1. Open `http://localhost:3000`
2. Press **Tab** — verify focus moves to the Name field with a visible focus ring
3. Press **Tab** again — verify focus moves to Email
4. Press **Tab** again — verify focus moves to Message
5. Press **Tab** again — verify focus moves to the Send Message button
6. Fill in all fields using the keyboard:
   - **Name:** `Zain Ahmed`
   - **Email:** `zain.ahmed@example.com`
   - **Message:** `What are the differences between the Free, Pro, and Enterprise plans? I'm considering an upgrade.`
7. Tab to the button and press **Enter**
8. Verify: the form submits successfully

---

## Testing Prompts

Ready-made prompts organized by type. Each prompt maps to one or more knowledge base articles. Use these to verify the agent answers from the KB instead of escalating.

### Simple Prompts (Single Turn)

| # | Prompt | Expected KB Match |
|---|--------|-------------------|
| S1 | `I just signed up. How do I create my first project and invite my team?` | Getting Started with Our Platform |
| S2 | `I forgot my password and can't log in. How do I reset it?` | How to Reset Your Password |
| S3 | `How do I change my profile picture and display name?` | Managing Your Account Settings |
| S4 | `What's included in the Pro plan? How much does it cost?` | Billing and Subscription Plans |
| S5 | `I see a charge on my invoice I don't recognize. Where can I view invoice history?` | Understanding Your Invoice |
| S6 | `My account is locked after too many failed login attempts. What do I do?` | Troubleshooting Login Issues |
| S7 | `The platform is loading really slowly today. Any suggestions?` | Troubleshooting Slow Performance |
| S8 | `How do I create a new project and organize it into folders?` | How to Create and Manage Projects |
| S9 | `How do task boards work? Can I add due dates and labels to tasks?` | Using the Task Management Feature |
| S10 | `I'm getting too many email notifications. How do I turn some off?` | Configuring Notification Settings |
| S11 | `Do you integrate with Slack and Jira? How do I set it up?` | Integrations Overview |
| S12 | `I need API access. Where do I generate an API key and what are the rate limits?` | API Documentation and Access |
| S13 | `Is our data encrypted? Are you SOC 2 compliant?` | Security and Data Privacy |
| S14 | `How can I export all my project data as JSON?` | How to Export Your Data |
| S15 | `How do I invite a new team member and assign them a role?` | Team Management and Roles |
| S16 | `I want to trigger an external workflow when a task is created. How do webhooks work?` | Using Webhooks for Automation |
| S17 | `How do I enable two-factor authentication on my account?` | How to Enable Two-Factor Authentication (2FA) |
| S18 | `I want to permanently delete my account. What happens to my data?` | How to Delete Your Account |

### Multi-Turn Conversations

Use these as sequential messages in a single session. After the first message, the form collapses to follow-up mode.

---

**Conversation A — New User Onboarding** (Name: `Hina Tariq`, Email: `hina.tariq@example.com`)

| Turn | Message |
|------|---------|
| 1 | `I just created my account. Can you walk me through how to set up my first project and invite my team?` |
| 2 | `Thanks! Now how do I set up the task board? I want to add columns like "In Review" and "QA".` |
| 3 | `Perfect. Can I connect this to our Slack channel so the team gets notified about task updates?` |
| 4 | `One last thing — how do I set quiet hours so I don't get notifications at night?` |

Expected KB matches: Getting Started → Task Management → Integrations → Notification Settings

---

**Conversation B — Security-Conscious Admin** (Name: `Bilal Hussain`, Email: `bilal.hussain@example.com`)

| Turn | Message |
|------|---------|
| 1 | `I'm the IT admin for our organization. What security certifications do you have? We need SOC 2 compliance.` |
| 2 | `Good. I need to enforce 2FA for all our users. How do I enable it?` |
| 3 | `What roles can I assign to team members? I want some users to only have read access.` |
| 4 | `Also, can I set up webhooks to monitor when new members join our workspace?` |

Expected KB matches: Security and Data Privacy → 2FA → Team Management and Roles → Webhooks

---

**Conversation C — Billing and Account Management** (Name: `Ayesha Malik`, Email: `ayesha.malik@example.com`)

| Turn | Message |
|------|---------|
| 1 | `We're currently on the Free plan. What do I get if I upgrade to Pro?` |
| 2 | `How will I be billed? Can I see past invoices somewhere?` |
| 3 | `I also need to change the email address on my account. How do I do that?` |
| 4 | `And how do I update my password while I'm at it?` |

Expected KB matches: Billing and Subscription Plans → Understanding Your Invoice → Managing Account Settings → How to Reset Your Password

---

**Conversation D — Developer Integration** (Name: `Usman Rauf`, Email: `usman.rauf@example.com`)

| Turn | Message |
|------|---------|
| 1 | `I need to integrate your platform with our internal tools via the API. Where do I start?` |
| 2 | `Got it. I want to get notified in real time when tasks are updated. Do you support webhooks?` |
| 3 | `Nice. Can I also export our project data programmatically for backup purposes?` |
| 4 | `The API seems a bit slow from our end. Any tips for improving performance?` |

Expected KB matches: API Documentation → Webhooks → How to Export Your Data → Troubleshooting Slow Performance

---

**Conversation E — Frustrated User with Escalation** (Name: `Sana Iqbal`, Email: `sana.iqbal@example.com`)

| Turn | Message |
|------|---------|
| 1 | `I've been locked out of my account for the second time this week. This is really frustrating. What's going on?` |
| 2 | `Fine. I've reset my password but the platform is still extremely slow. Is there an outage?` |
| 3 | `I want a full refund for this month. The service has been unusable.` |

Expected: Troubleshooting Login Issues → Troubleshooting Slow Performance → **Escalation to human** (refund request is out of scope per agent rules)

---

**Conversation F — Data and Compliance** (Name: `Farhan Sheikh`, Email: `farhan.sheikh@example.com`)

| Turn | Message |
|------|---------|
| 1 | `We're going through an audit. How do I export all our data including attachments?` |
| 2 | `What encryption standards do you use for data at rest and in transit?` |
| 3 | `One of our employees is leaving. How do I remove them from the team without losing their work?` |

Expected KB matches: How to Export Your Data → Security and Data Privacy → Team Management and Roles
