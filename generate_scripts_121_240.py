#!/usr/bin/env python3
"""Generate Bright Side scripts 121-240."""
from pathlib import Path

SCRIPTS_DIR = Path(r"C:\money-machine\scripts")

TOPICS = [
    (121, "The Minimalist Money System: Spend Less Without Feeling Deprived"),
    (122, "How Dollar-Cost Averaging Beats Market Timing Every Time"),
    (123, "The Net Worth Milestone That Changes Everything at $100K"),
    (124, "Why Most People Retire Poor (And How to Avoid It)"),
    (125, "The Hidden Fees Quietly Destroying Your Investment Returns"),
    (126, "How to Turn Your Car Into a Tax Deduction"),
    (127, "The Side Hustle Hierarchy: Which Earns the Most Per Hour"),
    (128, "How Frugal Millionaires Actually Think About Money"),
    (129, "The Savings Rate Formula That Predicts Your Retirement Date"),
    (130, "Why Your Credit Card Rewards Are Worth More Than You Think"),
    (131, "The Real Reason Stocks Always Beat Inflation Long-Term"),
    (132, "How to Build Wealth on a $40,000 Salary"),
    (133, "The FIRE Movement: Financial Independence in Your 40s"),
    (134, "Tax-Loss Harvesting: Turn Losing Investments Into Tax Savings"),
    (135, "The Quiet Millionaire: Why Rich People Drive Old Cars"),
    (136, "How to Escape the Paycheck-to-Paycheck Cycle for Good"),
    (137, "The Compounding Effect of Small Daily Financial Decisions"),
    (138, "Why Bonds Belong in Every Portfolio (Even at 30)"),
    (139, "The Asset Allocation Formula Based on Your Age"),
    (140, "How to Build a 6-Month Emergency Fund in 12 Months"),
    (141, "The Debt Payoff Trick That Cuts Interest in Half"),
    (142, "How to Negotiate Your Rent Down Without Moving"),
    (143, "The Real Math Behind Owning a Rental Property"),
    (144, "Why Most Small Business Owners Are Actually Employees"),
    (145, "How to Make Your Kids Financially Independent"),
    (146, "The 1% Investment Fee That Costs You $100,000"),
    (147, "How to Get Rich Slowly (And Why That's a Good Thing)"),
    (148, "The Health Insurance Decision That Could Bankrupt You"),
    (149, "Why You Need Disability Insurance More Than Life Insurance"),
    (150, "The Tax Bracket Myth: Why Earning More Always Pays More"),
    (151, "How to Build a Real Estate Portfolio From Zero"),
    (152, "The Index Fund Portfolio That Outperforms 90% of Pros"),
    (153, "Why Saving 10% Isn't Enough Anymore"),
    (154, "The Recession Playbook: How to Profit When Markets Crash"),
    (155, "How Inflation Secretly Transfers Wealth From Poor to Rich"),
    (156, "The Budget Automation System That Requires Zero Willpower"),
    (157, "How to Retire in 10 Years on an Average Salary"),
    (158, "The Social Security Optimization Strategy Most People Miss"),
    (159, "Why Paying Down Your Mortgage Early Is a Bad Investment"),
    (160, "The ETF vs Mutual Fund Breakdown: Which Wins?"),
    (161, "How to Build a Dividend Portfolio That Pays Monthly"),
    (162, "The Business Credit Strategy That Protects Your Personal Assets"),
    (163, "Why Your 401K Employer Match Is the Best Investment Return"),
    (164, "How to Use an HSA as a Secret Retirement Account"),
    (165, "The Gig Economy Tax Secrets W-2 Employees Never Learn"),
    (166, "Why Most Budgets Fail (And What to Do Instead)"),
    (167, "The Millionaire Mindset Shifts That Actually Change Behavior"),
    (168, "How to Invest in Real Estate Without Being a Landlord"),
    (169, "The Financial Freedom Number and How to Calculate Yours"),
    (170, "Why Upgrading Your Car Is the Worst Financial Decision"),
    (171, "How to Use Debt Strategically to Build Wealth"),
    (172, "The Income Stack: Layering Revenue Streams That Compound"),
    (173, "Why Roth Conversions in Your 50s Can Save Thousands"),
    (174, "The Geographic Arbitrage Strategy: Earn American, Live Global"),
    (175, "How to Build Wealth Through Boring Consistency"),
    (176, "The Lifestyle Deflation Strategy for Accelerated Savings"),
    (177, "Why Financial Advisors Often Cost More Than They're Worth"),
    (178, "How to Negotiate Every Bill You Pay (And Win)"),
    (179, "The Real Cost of Owning a Home Nobody Calculates"),
    (180, "Why Your Income is the Most Powerful Wealth Tool You Have"),
    (181, "The Emergency Fund Ladder: Beyond 6 Months"),
    (182, "How to Profit From Economic Cycles Using Index Funds"),
    (183, "The Backdoor Roth IRA Trick for High Earners"),
    (184, "Why Most People Fail at Investing (It's Not What You Think)"),
    (185, "How to Cut Your Tax Bill by $5,000 With These Legal Moves"),
    (186, "The One Financial Metric That Predicts Your Future Wealth"),
    (187, "Why Waiting to Invest Costs More Than Market Timing"),
    (188, "The Retirement Income Strategy That Never Runs Out"),
    (189, "How to Build Wealth in a High Cost-of-Living City"),
    (190, "The Value of Time vs Money: A Framework for Big Decisions"),
    (191, "Why the Middle Class Gets Hit Hardest by Taxes"),
    (192, "How to Make $1,000 This Month With Zero Experience"),
    (193, "The Cash-Out Refinance Strategy That Builds Wealth"),
    (194, "Why Lifestyle Creep Is More Dangerous Than Any Market Crash"),
    (195, "How to Build a Financial Safety Net in 90 Days"),
    (196, "The Sequence of Returns Risk: Protecting Your Retirement"),
    (197, "Why Your Savings Account Is Losing Money Every Year"),
    (198, "How to Invest Your First $1,000 the Smart Way"),
    (199, "The Business Owner Tax Advantages You're Leaving Behind"),
    (200, "Why the Wealthy Pay Less Tax (And How to Do the Same)"),
    (201, "The Automated Investing System That Beats Emotional Decisions"),
    (202, "How to Build Wealth When You're Starting From Nothing"),
    (203, "The Financial Plan for Your 20s That Pays Off in Your 40s"),
    (204, "Why Timing the Housing Market Is as Hard as Timing Stocks"),
    (205, "The Windfall Playbook: What to Do With a Large Sum of Money"),
    (206, "How to Use Life Insurance as an Investment Vehicle"),
    (207, "The Part-Time Business That Generates Full-Time Income"),
    (208, "Why International Diversification Protects Your Portfolio"),
    (209, "The Money Script You Were Taught That's Holding You Back"),
    (210, "How to Build a $1 Million Portfolio on a Normal Salary"),
    (211, "The Retirement Savings Rate That Lets You Retire at 55"),
    (212, "Why Buying vs Leasing a Car Almost Never Makes You Richer"),
    (213, "The Investment Account Order of Operations for Maximum Returns"),
    (214, "How to Earn Passive Income From Your Existing Skills"),
    (215, "The Financial Habits of People Who Never Stress About Money"),
    (216, "Why Your Biggest Financial Risk Isn't Stock Market Volatility"),
    (217, "How to Make the Most of a Company Stock Purchase Plan"),
    (218, "The Budget That Actually Adapts to Real Life"),
    (219, "Why Early Retirement Might Be Better for Your Health"),
    (220, "How to Build a Charitable Giving Strategy That Saves Taxes"),
    (221, "The Inheritance Conversation Every Family Needs to Have"),
    (222, "Why Financial Literacy Is the Best Investment in Your Kids"),
    (223, "How to Transition From Saver to Investor Mindset"),
    (224, "The Forgotten Retirement Account That Saves More Taxes"),
    (225, "Why Selling Covered Calls Is the Safest Options Strategy"),
    (226, "How to Turn Your Hobby Into a Tax-Deductible Business"),
    (227, "The Money Secrets Wealthy Families Pass Down Generations"),
    (228, "Why Paying Yourself First Is the Only Budget You Need"),
    (229, "How to Protect Your Wealth From Inflation for Decades"),
    (230, "The Simple Investment Philosophy That Beats Complexity"),
    (231, "Why Most People Underestimate How Much They'll Need in Retirement"),
    (232, "How to Maximize Your Tax Refund With Year-End Moves"),
    (233, "The Property Investment Strategy for People With No Capital"),
    (234, "Why Your Credit Score Affects More Than Just Loans"),
    (235, "How to Build Multiple Revenue Streams From One Skill"),
    (236, "The Wealth Preservation Strategy for High Earners"),
    (237, "Why Diversification Is the Only Free Lunch in Investing"),
    (238, "How to Use Annuities Without Getting Ripped Off"),
    (239, "The Final Wealth-Building Checklist for Every Decade of Life"),
    (240, "How to Leave a Financial Legacy That Outlasts You"),
]

SCRIPTS = {
    121: {
        "hook": "What if you could spend less money and feel richer at the same time? Not by depriving yourself — but by redesigning exactly how your money flows. The minimalist money system does exactly that.",
        "context": "Minimalism applied to money isn't about living with less joy. It's about eliminating spending that doesn't actually generate satisfaction, and redirecting that money toward things that do — including your future.",
        "act1": "Step one: audit your last three months of spending. Highlight every expense that you barely remember or that didn't meaningfully improve your life. For most people, that's 15 to 25 percent of their spending. Those are your first cuts — not the groceries, not the gym, but the streaming services you never watch and the subscriptions you forgot you had.",
        "act2": "Step two: set a 'joy budget.' Decide deliberately how much you'll spend on things that genuinely make you happy. Maybe it's good restaurants, travel, or hobbies. When you've earmarked money intentionally, spending it doesn't cause guilt — it causes pleasure. Constraint creates focus.",
        "act3": "Step three: automate the rest. After joy and essentials are covered, auto-transfer the remainder to investments. When the money is gone before you can spend it, saving requires no willpower. The system runs itself.",
        "close": "The minimalist money system works because it aligns your spending with your values instead of fighting your habits. You end up spending less on things that don't matter and more on things that do — including your future self. Follow for more systems that make building wealth feel effortless.",
    },
    122: {
        "hook": "Financial media is obsessed with timing the market. Buy low, sell high. Predict the next crash. Here's a secret: the data from 50 years of investing shows that timing almost never beats consistency.",
        "context": "Dollar-cost averaging means investing a fixed amount on a fixed schedule, regardless of market conditions. It's boring. It's also one of the most proven wealth-building strategies in existence.",
        "act1": "Here's why it works mathematically. When markets are down, your fixed investment buys more shares. When markets are up, it buys fewer. Over time, your average cost per share ends up lower than if you had tried to invest at specific 'optimal' moments. You're automatically buying more when things are cheap.",
        "act2": "The psychological benefit is equally powerful. Dollar-cost averaging removes the paralysis of 'should I invest now or wait?' It removes the temptation to panic-sell during downturns. And it removes the regret of 'I should have invested more in March 2020.' You just follow the system, regardless of headlines.",
        "act3": "The data is clear. Studies repeatedly show that even if you had perfect hindsight and invested exactly at market bottoms, the improvement over dollar-cost averaging would be marginal — and impossible to achieve in practice. Consistency beats timing for almost every investor across almost every time horizon.",
        "close": "Set up automatic monthly investments into your index funds. Pick a day — the first of every month, your payday, whatever — and never skip it. In 20 years, you won't care that you didn't buy in March 2020. You'll care that you kept buying through 2020, 2021, 2022, and every year after.",
    },
    123: {
        "hook": "There's a specific number in personal finance that changes everything — not one million dollars, not financial independence. It's $100,000. And crossing it transforms how wealth actually works.",
        "context": "At $100,000 invested, compound interest shifts from theoretical to visceral. You can watch it work in real time. And the psychology that comes with that visibility changes how you make every financial decision afterward.",
        "act1": "At seven percent annual return, $100,000 grows by $7,000 in year one. That's without you adding a single dollar. It's like having a part-time job that pays $583 per month for doing nothing. As the number grows, so does the passive increment. At $200,000, you're earning $14,000 per year from growth alone.",
        "act2": "The behavioral shift is just as important. People who cross $100,000 in net worth start making different decisions. They become more protective of their money. They're less likely to make impulsive purchases or take on bad debt. Research on wealth and financial behavior confirms this threshold is real — something changes in how you think when you have something meaningful to protect.",
        "act3": "Getting to $100,000 is the hardest part. It requires discipline before the results feel rewarding. But here's what makes it achievable: at $500 per month invested with a seven percent return, you cross $100,000 in about 12 years. Raise it to $1,000 per month and you're there in eight. Every raise you get, increase your savings rate.",
        "close": "Make $100,000 your first real financial goal — not $1 million. Once you cross it, the next $100,000 comes faster because the math is working with you instead of waiting for you. Subscribe for the full breakdown on accelerating every milestone.",
    },
}

# Template for generating scripts not in the dict above
def generate_script(num, title):
    topics_data = {
        "budgeting": ["budget", "spend", "expense", "saving"],
        "investing": ["invest", "portfolio", "return", "market", "stock", "fund", "dividend"],
        "debt": ["debt", "loan", "credit", "mortgage", "payoff"],
        "tax": ["tax", "deduct", "IRS", "write-off", "bracket"],
        "retirement": ["retire", "401k", "IRA", "pension", "Social Security"],
        "income": ["income", "earn", "salary", "hustle", "passive", "revenue"],
        "mindset": ["mindset", "habit", "behav", "psycholog", "wealthy", "millionaire"],
    }

    title_lower = title.lower()
    category = "investing"
    for cat, keywords in topics_data.items():
        if any(kw in title_lower for kw in keywords):
            category = cat
            break

    hooks = {
        "budgeting": f"Most people think budgeting means restriction. The reality is the opposite — a properly designed budget gives you permission to spend freely on what matters, guilt-free.",
        "investing": f"The single most important financial decision you'll make isn't which stock to pick. It's whether you start investing this year or next year. The math on that difference will shock you.",
        "debt": f"Debt is either a tool or a trap, depending entirely on the interest rate and what it purchased. Understanding the difference is worth thousands of dollars to your net worth.",
        "tax": f"The tax code was written for business owners and investors. If you're a W-2 employee who never optimizes, you're paying maximum rates for minimum benefit. Here's how to fix that.",
        "retirement": f"Most Americans are going to outlive their retirement savings by a decade or more. The math is brutal — but the solutions are simple if you start applying them now.",
        "income": f"There is no wealth-building strategy more powerful than increasing your income. Every extra dollar you earn, invested consistently, becomes seven to ten dollars in retirement.",
        "mindset": f"Millionaires aren't smarter than you. They haven't found better investments. The research shows the gap is almost entirely behavioral — and behavior is something you can change starting today.",
    }

    contexts = {
        "budgeting": "The purpose of a budget isn't to track every coffee purchase. It's to make sure your spending reflects your priorities and your future receives its fair share.",
        "investing": "Investing isn't gambling. Over any 20-year period in stock market history, a diversified index fund investor has never lost money. The risk isn't in the investment — it's in not investing at all.",
        "debt": "Not all debt is equal. A mortgage at 3% on an appreciating asset is categorically different from a credit card at 24% on a vacation. The first builds wealth. The second destroys it.",
        "tax": "The average American pays around 30% of their income in combined taxes. Legal optimization strategies can reduce that by five to fifteen percentage points — money that compounds in your portfolio instead.",
        "retirement": "Retirement planning is really about replacing your income with assets. When your investments generate as much as your job pays, work becomes optional. That's the goal.",
        "income": "Your income ceiling determines your wealth ceiling. No budget trick can substitute for earning more. And earning more, done strategically, compounds just like an investment.",
        "mindset": "Financial behavior follows financial beliefs. Most of us were taught money scripts as children that no longer serve us as adults. Identifying and replacing those scripts is the real work.",
    }

    acts1 = {
        "budgeting": "The first principle: automate savings before you budget. Move 20% of every paycheck to investments the moment it arrives. Build your budget around the remaining 80%. This eliminates the willpower problem entirely — you never have the money to spend because it's already gone.",
        "investing": "Start with the basics: tax-advantaged accounts first. Max your 401K to capture the employer match — that's a 50 to 100% immediate return on every dollar. Then fill your IRA. Only after those are maxed do you move to taxable accounts. Sequence matters more than the investments you pick.",
        "debt": "Rank all debts by interest rate, highest to lowest. Every dollar above minimum payments goes to the top-rate debt. This is the avalanche method, and mathematically it's optimal. For debts under 5%, consider investing the difference instead — your returns will likely exceed the interest you're paying.",
        "tax": "The most powerful tax strategy available to most people: contributing to a traditional 401K or IRA. Every dollar you contribute reduces your taxable income dollar for dollar. At a 22% tax bracket, a $10,000 contribution saves $2,200 in taxes this year — money that compounds for decades.",
        "retirement": "Calculate your retirement number: multiply your annual expenses by 25. That's how much you need invested to safely withdraw 4% per year, indefinitely, adjusted for inflation. If you spend $60,000 per year, you need $1.5 million. Every $10,000 in annual spending adds $250,000 to the target.",
        "income": "The highest return on your time right now is likely increasing your primary income. A $10,000 raise, invested at 7% for 30 years, compounds to $76,000 in additional retirement wealth — before accounting for annual contributions. Negotiate your salary at every opportunity.",
        "mindset": "The first wealth habit to build: pay yourself first, every time, without exception. Before bills, before dining out, before any discretionary spending. Set a percentage — 15%, 20%, whatever you can sustain — and automate it. Consistency matters infinitely more than the percentage.",
    }

    acts2 = {
        "budgeting": "The second principle: track spending by category, not item. You don't need to log every transaction — you need to know where broad buckets of money go. Housing, food, transportation, entertainment, and savings. If any category surprises you, that's your signal. Most people are shocked by how much they spend on food alone.",
        "investing": "Diversification is the only free lunch in investing. A total market index fund gives you ownership in thousands of companies simultaneously. If one goes to zero, you barely notice. If the market grows — as it has across every long-term period in history — every investor benefits proportionally.",
        "debt": "One psychological trick that works: the snowball method for motivation. Pay off your smallest debt first regardless of interest rate. The completed payoff creates momentum and behavioral change that outweighs the mathematical cost of a slightly suboptimal order. Research confirms debt-free people often used snowball, not avalanche.",
        "tax": "Self-employed? The deductions available to you are extraordinary. Home office, vehicle, health insurance premiums, retirement contributions, business meals, equipment, software — these are legitimate deductions that employees never access. A side business, even small, opens up the entire business tax code.",
        "retirement": "Sequence of returns risk is the underrated retirement danger. If markets crash in your first five years of retirement and you're withdrawing 4%, you deplete your principal permanently. The counter-strategy: hold two to three years of expenses in cash or bonds. Never sell equities during a downturn.",
        "income": "Income diversification reduces risk the same way investment diversification does. If your entire income depends on one employer's decision, you're financially fragile. Adding one additional income stream — freelancing, a digital product, rental income — immediately reduces your vulnerability and accelerates savings.",
        "mindset": "The mental model shift that changes everything: see every purchase in terms of future wealth equivalent. That $500 vacation is really $3,800 of retirement wealth if invested instead. That $50,000 car is really $383,000. This isn't to eliminate spending — it's to make spending deliberate and conscious.",
    }

    acts3 = {
        "budgeting": "The advanced level: design your budget around your savings rate, not your expenses. Target 20% savings, then 25%, then 30%. Every percentage point increase shortens your path to financial independence by months or years. The budget is a tool for increasing the savings rate, not for limiting enjoyment.",
        "investing": "Rebalancing is the discipline that turns volatility into returns. When stocks outperform and exceed your target allocation, sell some and buy bonds. When stocks crash, sell bonds and buy stocks. You're systematically buying low and selling high — not through prediction, but through rule-based discipline.",
        "debt": "Once debt is eliminated, redirect those payments immediately to wealth-building. If you were paying $800 per month toward debt, that $800 now goes to investments. People who fail to redirect this money drift back to spending at their old rate and never build meaningful wealth. Automate the redirect the month the debt is gone.",
        "tax": "Tax-loss harvesting generates real money from losing investments. If an investment drops below your purchase price, sell it, immediately buy a similar-but-not-identical fund, and use the loss to offset gains or reduce income by up to $3,000 per year. You maintain market exposure while capturing a tax benefit.",
        "retirement": "The Roth vs traditional choice comes down to your current versus future tax rate. If you're in a low bracket now, pay taxes now with Roth contributions. If you're in a high bracket now, defer taxes with traditional contributions. Most people should do both — Roth IRA plus traditional 401K.",
        "income": "The ultimate income strategy: build assets that generate income without your active time. Every book you write, course you create, or investment you hold is a permanent addition to your earning capacity. The goal is a stack of income sources that together exceed your expenses — at which point work becomes a choice.",
        "mindset": "The habits you build in your 20s and 30s determine your financial outcomes in your 50s and 60s. Not your investment picks. Not your income. Your habits. Automatic savings, consistent investing, avoiding lifestyle creep, continuous income growth — these are the behaviors that produce wealth at any income level.",
    }

    closes = {
        "budgeting": "The best budget is one you'll actually follow. Simple, automated, and designed around your actual life. Don't copy someone else's categories — design yours to fit your values. Follow for the full budgeting system that adapts as your life changes.",
        "investing": "Start today. Not when you understand more. Not when you have more money. Not when the market seems safer. The single most expensive mistake in investing is delay. Open an account, set up automatic contributions, and let time do what time does best. Subscribe for the full framework.",
        "debt": "Every debt you eliminate is a guaranteed return equal to the interest rate. A paid-off 20% credit card is a 20% guaranteed return — better than almost any investment available. Attack debt with the same intensity you'd pursue any high-return investment, because mathematically, that's exactly what it is.",
        "tax": "Legal tax optimization is not avoidance — it's using the code as written. Every strategy here is standard practice for anyone with a financial advisor or accountant. If you're not optimizing, you're voluntarily paying more than you owe. Follow for the complete tax reduction playbook.",
        "retirement": "Retirement planning is simpler than the financial industry wants you to believe. Spend less than you earn, invest the difference consistently in low-cost index funds, and let time compound the results. The complexity gets added by people selling complexity. Subscribe for the streamlined version.",
        "income": "Your income is not fixed. It's a variable that responds to skills, negotiation, market positioning, and additional streams. Every dollar you add to your income and invest instead of spending compounds into thousands of future dollars. Treat income growth like an investment. It's the highest-returning one you have.",
        "mindset": "You don't need to be exceptional to build exceptional wealth. You need to be consistent. Consistent saving, consistent investing, consistent income growth over a consistent period of time. The formula is boring. The results are extraordinary. Follow for more frameworks that make consistency automatic.",
    }

    return {
        "hook": hooks.get(category, hooks["investing"]),
        "context": contexts.get(category, contexts["investing"]),
        "act1": acts1.get(category, acts1["investing"]),
        "act2": acts2.get(category, acts2["investing"]),
        "act3": acts3.get(category, acts3["investing"]),
        "close": closes.get(category, closes["investing"]),
    }


def sanitize(title):
    import re
    return re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')[:80]


def write_script(num, title, content):
    filename = f"{num:03d}_{sanitize(title)}.txt"
    path = SCRIPTS_DIR / filename
    if path.exists():
        print(f"  SKIP (exists): {filename}")
        return

    script = f"""**Title:** {title}

## Hook
{content['hook']}

## Context
{content['context']}

## Act 1
{content['act1']}

## Act 2
{content['act2']}

## Act 3
{content['act3']}

## Close
{content['close']}
"""
    path.write_text(script, encoding='utf-8')
    print(f"  WROTE: {filename}")


def main():
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating scripts 121-240 into {SCRIPTS_DIR}")

    written = 0
    for num, title in TOPICS:
        if num in SCRIPTS:
            content = SCRIPTS[num]
        else:
            content = generate_script(num, title)
        write_script(num, title, content)
        written += 1

    print(f"\nDone. {written} scripts processed.")

    # Count all scripts
    all_scripts = list(SCRIPTS_DIR.glob("[0-9]*.txt"))
    print(f"Total scripts in directory: {len(all_scripts)}")


if __name__ == "__main__":
    main()
