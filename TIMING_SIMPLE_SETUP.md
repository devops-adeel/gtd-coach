# Timing + GTD Integration: 5-Minute Setup Guide

## The ADHD-Friendly Approach: Keep It Simple!

This guide helps you organize Timing for GTD in just 5 minutes. No complex hierarchies, no overwhelming options - just 5 projects and a few simple rules.

## Step 1: Run the Analysis (1 minute)

First, see what you're actually tracking:

```bash
# Using Docker (recommended)
./docker-run.sh analyze-timing

# Or if you have Python environment set up
python3 analyze_timing.py
```

This shows:
- What you're currently tracking
- How your time is distributed
- Simple suggestions for organization

## Step 2: Create 5 Projects in Timing (2 minutes)

Open Timing app and create exactly these 5 projects:

1. **GTM Strategy Work** 
   - Color: Blue
   - For: Agentic AuthZ work, strategy docs, planning

2. **AI Factory Work**
   - Color: Green  
   - For: AWS Bedrock, implementation, technical work

3. **Arabic Learning**
   - Color: Yellow
   - For: Duolingo, Classical Arabic study, language tools

4. **Claude Development**
   - Color: Purple
   - For: Learning Claude, building AI tutor, coding projects

5. **Other/Admin**
   - Color: Gray
   - For: Everything else (email, browsing, admin tasks)

**How to create a project in Timing:**
1. Click the "+" button in the Projects sidebar
2. Enter the project name
3. Choose a color
4. Click "Create"

That's it! Don't create sub-projects or hierarchies.

## Step 3: Set Up Quick Rules with ⌥-Drag (2 minutes)

This is the magic part - Timing's ⌥-drag feature makes rule creation visual and instant:

1. **Find Duolingo in your activities list**
   - Hold ⌥ (Option key)
   - Drag it onto "Arabic Learning" project
   - ✅ All future Duolingo time auto-categorizes!

2. **Find Microsoft Teams**
   - ⌥-drag onto "GTM Strategy Work"
   - ✅ All Teams meetings now tracked as GTM work!

3. **Find AWS Console (in browser activities)**
   - ⌥-drag onto "AI Factory Work"
   - ✅ AWS work auto-categorizes!

4. **Find Terminal/Ghostty sessions with "arabic" in title**
   - ⌥-drag onto "Arabic Learning"
   - ✅ Arabic coding sessions tracked!

5. **Leave Claude.ai uncategorized**
   - You'll manually assign this based on context

## Step 4: Set Up Project Switching Shortcut (30 seconds)

1. Open Timing → Preferences → Shortcuts
2. Set "Switch Project" to: **⌃⌥⌘P**
3. Now you can quickly switch projects without leaving your current app!

## Step 5: The Weekly Review Connection

During your GTD weekly review, you'll now see:
- Actual time spent on each of your 5 projects
- Comparison with your intended priorities
- Clear picture of where time really goes

The `gtd-review.py` will automatically pull this data during the STARTUP phase!

## How to Use Day-to-Day

### The ADHD-Friendly Workflow:

1. **Let Timing track automatically** (it's always running)
2. **When you notice you switched projects**: Hit ⌃⌥⌘P and select the right project
3. **If you forget**: That's OK! It goes to Other/Admin
4. **Once a week**: During GTD review, batch-categorize anything important
5. **Don't stress about perfection**: 80% accurate is perfect for ADHD

### What NOT to Do:
- ❌ Don't create complex hierarchies
- ❌ Don't try to categorize everything perfectly
- ❌ Don't check Timing multiple times per day
- ❌ Don't create more than 5 main projects
- ❌ Don't feel bad if you forget to categorize for days

## Quick Reference

| Project | Keyboard Marker | What Goes Here |
|---------|----------------|----------------|
| GTM Strategy | Work hours, Teams | Strategy, planning, AuthZ |
| AI Factory | AWS, technical | Bedrock, implementation |
| Arabic Learning | Duolingo, LMStudio | All language study |
| Claude Development | Claude.ai, VS Code | Coding, AI tutor |
| Other/Admin | Everything else | Email, browsing, misc |

## Troubleshooting

**"I have too many auto-generated app projects!"**
- That's normal! Just ⌥-drag the important ones to your 5 projects
- Ignore the rest - they don't matter

**"I forgot to categorize for 3 days!"**
- Perfect! Do it during weekly review
- Or just let it be in Other/Admin

**"Should I create more projects?"**
- No! Stick with 5. Simplicity > Precision

**"What about personal vs work time?"**
- Your 5 projects already separate them
- Don't overthink it

## The 80/20 Rule for ADHD

Remember: 
- 5 projects capture 80% of what matters
- 5 rules categorize 80% automatically  
- Checking once per week is 80% as good as daily
- 80% accurate is 100% good enough!

## Next Steps

1. ✅ Run `analyze_timing.py` to see your data
2. ✅ Create the 5 projects in Timing
3. ✅ Set up 5 quick rules with ⌥-drag
4. ✅ Configure ⌃⌥⌘P shortcut
5. ✅ Run your next GTD review to see it in action!

Total time: 5 minutes to organized time tracking! 🎉