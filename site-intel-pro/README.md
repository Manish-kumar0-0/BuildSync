# Site Intel Pro

Build a premium, modern, mobile-first frontend prototype for an AI-powered Construction Intelligence and Project Management App.

IMPORTANT:

This phase is ONLY for the MOBILE APPLICATION FRONTEND.

Do NOT create:

- Admin website

- Government website

- Backend

- Database

- Real APIs

- Authentication server

- AI models

Use mock data and frontend-only interactions.

The goal is to create a realistic, high-quality mobile app UI that can later be connected to a backend and AI services.

====================================================

PRODUCT CONCEPT

====================================================

The application is a centralized Construction Intelligence Platform used by people working inside a large construction project.

The app connects:

- Workers

- Foremen

- Field Engineers

- Site Engineers

- Safety Officers

- QA/QC Engineers

- Store/Material Managers

- Drivers

- Equipment Managers

- Project Managers

Every user logs into the SAME mobile app.

After login, the interface changes according to the user's role.

Each role should only see features relevant to their responsibilities.

The core product flow is:

CAPTURE

↓

VERIFY

↓

TRACK

↓

ANALYZE

↓

PREDICT

↓

RECOVER

The app should feel like a real construction technology platform, not a simple task management application.

====================================================

VISUAL DESIGN DIRECTION

====================================================

Use a premium dark enterprise design inspired by modern geospatial and construction intelligence platforms.

Design characteristics:

- Dark premium interface

- Industrial technology feeling

- Minimal

- Clean

- Professional

- High-tech

- Enterprise SaaS

- Data-driven

- Strong visual hierarchy

- Thin borders

- Dark cards

- Minimal shadows

- Spacious layouts

- Premium analytics

The UI should feel similar to a professional construction intelligence dashboard.

Do NOT make it look like:

- A student project

- A generic todo app

- A colorful social media app

- A gaming app

- A generic AI chatbot

====================================================

COLOR SYSTEM

====================================================

Use a dark UI.

Main Background:

#111116

Secondary Background:

#17171D

Card Background:

#1E1E26

Elevated Surface:

#24242D

Borders:

#2E2E38

PRIMARY BRAND ACCENT:

Parrot Green:

#C6E84A

Alternative Green:

#B8E637

Use Parrot Green for:

- Primary buttons

- Active navigation

- Important actions

- Progress highlights

- Selected items

- Main CTAs

- Important metrics

SUCCESS GREEN:

#32C76B

Use only for:

- Completed

- Verified

- On Track

- Success

DANGER RED:

#FF4D4D

Use only for:

- High risk

- Delayed activities

- Critical issues

- Safety danger

- Emergency alerts

WARNING:

#F5A524

Use for:

- Medium risk

- Pending

- Under review

- Attention needed

PRIMARY TEXT:

#F5F5F5

SECONDARY TEXT:

#9B9BA3

MUTED TEXT:

#666670

IMPORTANT COLOR RULE:

Parrot Green is the PRIMARY BRAND COLOR.

Normal Green represents SUCCESS.

Red represents DANGER.

Do not overuse bright colors.

Most of the interface should remain dark and minimal.

====================================================

TYPOGRAPHY

====================================================

Use a clean modern sans-serif font.

Typography hierarchy:

Large bold dashboard headings

Medium bold section headings

Readable body text

Small muted metadata

The typography should feel like a premium enterprise SaaS product.

====================================================

APP STRUCTURE

====================================================

Create ONE mobile application with role-based dashboards.

Roles:

1. Worker

2. Foreman

3. Field Engineer

4. Site Engineer

5. Safety Officer

6. QA/QC Engineer

7. Store / Material Manager

8. Driver

9. Equipment Manager

10. Project Manager

For prototype purposes, create a demo role selector after login.

This allows easy switching between dashboards.

====================================================

COMMON SCREENS

====================================================

Create:

1. Splash Screen

2. Welcome Screen

3. Login Screen

4. Demo Role Selection

5. Forgot Password

6. OTP Verification

7. Notifications

8. Profile

9. Settings

Login screen should be minimal and premium.

====================================================

WORKER DASHBOARD

====================================================

Keep the Worker interface simple.

Include:

- Greeting

- Worker name

- Current project

- Attendance status

- Today's assigned task

- Task progress

- Work location

- Safety instructions

- Report issue

- Recent notifications

- Work history

Bottom navigation:

Home

Tasks

Report

Profile

====================================================

FOREMAN DASHBOARD

====================================================

Include:

- Team attendance

- Workers present

- Workers absent

- Today's activities

- Team progress

- Assign workers

- Worker list

- Site issues

- Recent activity timeline

====================================================

FIELD ENGINEER DASHBOARD

====================================================

This is one of the MOST IMPORTANT dashboards.

The Field Engineer is responsible for recording and uploading site evidence.

Dashboard should include:

- Current project

- Today's assigned activities

- Progress summary

- Pending evidence uploads

- Recent evidence

- GPS status

- Site conditions

- Recent issues

The PRIMARY ACTION should be highly visible:

CAPTURE SITE EVIDENCE

Create a large prominent action button.

Evidence Capture Flow:

Select Project

↓

Select Construction Activity

↓

Capture Photo

OR

Record Video

↓

Automatically display GPS

↓

Automatically display Timestamp

↓

Add Progress Percentage

↓

Add Notes

↓

Submit Evidence

Create these screens:

- Evidence Capture

- Camera UI

- Video Recording UI

- Media Preview

- Select Activity

- Add Progress

- Add Notes

- Upload Confirmation

- Evidence History

Evidence cards should show:

- Media thumbnail

- Activity name

- Location

- Timestamp

- Submitted by

- Verification status

Status colors:

Verified = Success Green

Under Review = Amber

Issue / Mismatch = Red

====================================================

SITE ENGINEER DASHBOARD

====================================================

Include:

- Overall site progress

- Today's activities

- Active workforce

- Material availability

- Equipment status

- Evidence waiting for review

- Delayed activities

- Critical issues

- AI alerts

Important actions:

- Review Evidence

- Verify Activity

- Assign Tasks

- Report Issue

- View Delay Risk

- View Recovery Plan

Create Evidence Verification Screen.

Example:

Activity:

Pier P3 Construction

Planned Progress:

70%

Reported Progress:

65%

AI Estimated Progress:

63%

Status:

Needs Review

Actions:

Approve

Reject

Request More Evidence

====================================================

SAFETY OFFICER DASHBOARD

====================================================

Include:

- Safety Score

- Open Hazards

- Critical Incidents

- PPE Compliance

- Safety Inspections

- Incident Reports

- Emergency Alerts

Critical alerts should visually use Red.

====================================================

QA/QC ENGINEER DASHBOARD

====================================================

Include:

- Pending Inspections

- Quality Score

- Defects

- Rework Tasks

- Test Results

- Inspection Checklist

- Evidence Upload

Create a detailed inspection checklist interface.

====================================================

STORE / MATERIAL MANAGER DASHBOARD

====================================================

Include:

- Inventory Overview

- Low Stock Alerts

- Material Received

- Material Issued

- Material Movement

- Supplier Information

- Vehicle Delivery Details

Create screens:

- Add Material

- Material Received

- Material Issued

- Inventory List

- Material Details

- Low Stock Alerts

Example material card:

Steel Bars

Received: 50 Tons

Used: 35 Tons

Remaining: 15 Tons

Status: Healthy

====================================================

DRIVER DASHBOARD

====================================================

Keep the Driver interface simple.

Include:

- Current Trip

- Vehicle Number

- Material Being Transported

- Pickup Location

- Destination

- Start Trip

- Delivery Confirmation

- Trip History

Include a dark map-style location interface.

====================================================

EQUIPMENT MANAGER DASHBOARD

====================================================

Include:

- Equipment Overview

- Active Equipment

- Idle Equipment

- Under Maintenance

- Usage Hours

- Breakdown Reports

- Maintenance Schedule

Use clear equipment status indicators.

====================================================

PROJECT MANAGER DASHBOARD

====================================================

This should be the most advanced and premium dashboard.

The Project Manager should see the overall health of the project.

Main Dashboard:

PROJECT HEALTH

Status:

ON TRACK

AT RISK

DELAYED

Show:

- Overall Progress

- Workers Present

- Active Activities

- Delayed Activities

- Critical Issues

- Material Status

- Equipment Status

Create analytics sections:

- Planned vs Actual Progress

- Activity Performance

- Workforce Trends

- Material Status

- Delay Risk

- Critical Issues

- Recent Site Events

Use premium dark charts.

====================================================

AI INSIGHTS

====================================================

Create a dedicated AI Intelligence section.

Screens:

1. AI Risk Prediction

2. Root Cause Analysis

3. Recovery Recommendation

4. AI Construction Copilot

Example AI Risk Card:

ACTIVITY AT RISK

Pier P3 Construction

Risk Level:

HIGH

Predicted Delay:

3 Days

Main Causes:

- Worker shortage

- Material delay

- Rain interruption

Use Red for high risk.

====================================================

AI RECOVERY PLAN

====================================================

Create a premium Recovery Plan interface.

Example:

ACTIVITY AT RISK

Pier P3 Construction

Current Progress:

62%

Planned Progress:

75%

Predicted Delay:

3 Days

AI RECOMMENDED RECOVERY PLAN

OPTION 1

Add:

8 Workers

Expected Recovery:

3 Days

OPTION 2

Add:

4 Workers

+

1 Additional Machine

Expected Recovery:

2 Days

OPTION 3

Increase Shift Duration

Expected Recovery:

2 Days

Actions:

Review

Approve Plan

Reject

Modify Recommendation

This should look like an intelligent decision-support interface.

====================================================

CONSTRUCTION EVENT TIMELINE

====================================================

Create a Construction Event Timeline.

Every important project action becomes a digital event.

Example:

09:00

Workers Arrived

10:00

Foundation Work Started

11:30

Steel Delivered

13:15

Field Engineer Uploaded Evidence

14:30

Equipment Issue Reported

16:00

Rain Interruption

Each event should display:

WHO

WHAT

WHERE

WHEN

Include event icons and status indicators.

====================================================

CONSTRUCTION REPLAY

====================================================

Create a premium Construction Replay feature.

User can select:

- Date

- Activity

- Location

Then view a chronological replay of site events.

Example:

09:00

Workers Arrived

10:00

Work Started

11:30

Material Delivered

13:00

Photo Evidence Uploaded

14:30

Rain Started

15:00

Work Stopped

When clicking an event show:

- Photo

- Video preview

- GPS location

- Person

- Timestamp

- Activity

- Notes

Use timeline + map inspired UI.

This should be one of the visually strongest features.

====================================================

AI CONSTRUCTION COPILOT

====================================================

Create an AI chatbot interface specifically for construction project intelligence.

Example questions:

Why is Pier P3 delayed?

Which activity has the highest risk?

How many workers should be added?

What happened yesterday?

Show:

- Suggested questions

- Chat history

- AI insight cards

- Related project data

- Actionable recommendations

Do NOT make it look like a generic ChatGPT interface.

Make it look like a professional Construction Intelligence Copilot.

====================================================

NAVIGATION

====================================================

Navigation must change according to the user's role.

Example:

PROJECT MANAGER:

Home

Projects

Analytics

AI Insights

Profile

FIELD ENGINEER:

Home

Activities

Capture

Evidence

Profile

WORKER:

Home

Tasks

Report

Profile

Navigation should be simple and mobile friendly.

====================================================

REUSABLE UI COMPONENTS

====================================================

Create reusable components:

- Metric Cards

- Status Badges

- Progress Bars

- Risk Indicators

- Activity Cards

- Evidence Cards

- Timeline Events

- AI Insight Cards

- Alert Cards

- Project Cards

- Material Cards

- Equipment Cards

- User Cards

- Bottom Sheets

- Confirmation Dialogs

Use:

- Rounded corners around 14-18px

- Thin borders

- Minimal shadows

- Spacious padding

- Clean alignment

Avoid excessive glassmorphism.

====================================================

DATA VISUALIZATION

====================================================

Use professional data visualization.

Include:

- Line Charts

- Bar Charts

- Circular Progress

- Progress Timelines

- Risk Indicators

- Activity Performance Charts

Color usage:

Parrot Green = Primary positive data

Success Green = Verified/completed

Red = Negative/danger

Amber = Warning

Charts must look clean on dark backgrounds.

====================================================

MAP AND LOCATION UI

====================================================

Include map-inspired interfaces where relevant.

Examples:

- Construction site location

- Evidence location

- Driver location

- Vehicle movement

- Construction zones

Use dark map styling.

====================================================

INTERACTIONS

====================================================

Create frontend-only interactions.

Include:

- Role switching

- Screen navigation

- Tabs

- Filters

- Date selection

- Bottom sheets

- Modals

- Evidence preview

- Timeline interaction

- Mock AI responses

- Status changes

Use realistic mock construction project data.

====================================================

IMPORTANT PRODUCT IDENTITY

====================================================

This is NOT just a construction management app.

It is a:

CONSTRUCTION INTELLIGENCE PLATFORM

The interface should communicate:

REAL SITE DATA

+

SITE EVIDENCE

+

PROJECT TRACKING

+

AI ANALYSIS

+

RISK PREDICTION

+

RECOVERY DECISIONS

====================================================

FINAL DESIGN GOAL

====================================================

Create a polished, premium, production-quality mobile application frontend.

The app should feel like a high-end construction technology startup product used on large infrastructure projects.

The visual experience should communicate:

CAPTURE

↓

VERIFY

↓

TRACK

↓

ANALYZE

↓

PREDICT

↓

RECOVER

Prioritize:

- Premium visual quality

- Mobile-first UX

- Clear role-based dashboards

- Realistic construction workflows

- Strong analytics

- AI intelligence UI

- Dark enterprise design

- Parrot Green brand identity

- Red for danger and critical risks

Do not create any website in this phase.

Build ONLY the mobile application frontend. 
 give me codeblock frontend

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/3f6d9210-393c-4cc1-948a-41c3d2bc1949).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
