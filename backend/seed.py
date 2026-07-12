"""
Idempotent seed data for EcoSphere: Indian manufacturing company (Bharti Industries).
- 5 departments with hierarchy and 25 employees
- Emission factors (v1 + v2 revisions): diesel, electricity, purchase-spend
- 60 operational records across 3 months
- 4 CSR activities
- 5 challenges in mixed lifecycle states
- 6 badges, 5 rewards
- 3 policies with partial acknowledgements
- 2 audits, 4 compliance issues (1 overdue)
- Scores ~70-90 across E/S/G

Run: python -m backend.seed
"""

import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from app.db import SessionLocal, engine
from app.models import (
    Audit,
    Badge,
    Category,
    CategoryType,
    Challenge,
    ChallengeLifecycle,
    ChallengeParticipation,
    CarbonTransaction,
    ComplianceIssue,
    CSRActivity,
    DataTier,
    Department,
    DepartmentScore,
    EmployeeParticipation,
    EmissionFactor,
    EnvironmentalGoal,
    ESGPolicy,
    OpType,
    OperationalRecord,
    PointTransaction,
    PolicyAcknowledgement,
    Reward,
    RewardRedemption,
    User,
    UserBadge,
    UserRole,
)


def hash_password(password: str) -> str:
    """Hash password using bcrypt.

    bcrypt is a hard requirement (see requirements.txt); there is deliberately no
    insecure SHA-256 fallback — a missing bcrypt must fail loudly, not silently
    seed unverifiable password hashes.
    """
    import bcrypt

    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def truncate_all_tables(db):
    """Truncate all tables in dependency order (idempotent)."""
    tables = [
        "esg_ledger",
        "reward_redemptions",
        "point_transactions",
        "user_badges",
        "challenge_participation",
        "employee_participation",
        "csr_activities",
        "policy_acknowledgements",
        "challenges",
        "badges",
        "rewards",
        "compliance_issues",
        "audits",
        "esg_policies",
        "carbon_transactions",
        "operational_records",
        "environmental_goals",
        "department_scores",
        "notifications",
        "users",
        "departments",
        "categories",
        "product_esg_profiles",
        "emission_factors",
        "settings",
    ]

    for table in tables:
        try:
            db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        except Exception:
            pass
    db.commit()


def seed_db():
    """Seed the database with test data."""
    db = SessionLocal()

    try:
        # Truncate all tables (idempotent)
        truncate_all_tables(db)
        print("✓ Tables truncated")

        # =========== 1. DEPARTMENTS (5 with hierarchy) ===========
        dept_root = Department(name="Bharti Industries", code="BHI")
        db.add(dept_root)
        db.flush()

        depts = {
            "mfg": Department(
                name="Manufacturing",
                code="MFG",
                parent_id=dept_root.id,
            ),
            "logistics": Department(
                name="Logistics & Supply Chain",
                code="LOG",
                parent_id=dept_root.id,
            ),
            "corporate": Department(
                name="Corporate Affairs",
                code="CRP",
                parent_id=dept_root.id,
            ),
            "rnd": Department(
                name="Research & Development",
                code="RND",
                parent_id=dept_root.id,
            ),
            "sales": Department(
                name="Sales & Marketing",
                code="SAL",
                parent_id=dept_root.id,
            ),
        }

        for dept in depts.values():
            db.add(dept)
        db.flush()
        print("✓ 5 departments created")

        # =========== 2. USERS (25 employees + managers) ===========
        users_data = [
            # Corporate team
            ("ceo@bharti.in", "Rajesh Kumar", "ADMIN", "corporate"),
            ("cfo@bharti.in", "Priya Sharma", "MANAGER", "corporate"),
            ("csr_head@bharti.in", "Anita Patel", "MANAGER", "corporate"),
            ("corp1@bharti.in", "Vikram Singh", "EMPLOYEE", "corporate"),
            ("corp2@bharti.in", "Divya Mishra", "EMPLOYEE", "corporate"),

            # Manufacturing team
            ("mfg_head@bharti.in", "Anil Kapoor", "MANAGER", "mfg"),
            ("mfg_eng1@bharti.in", "Suresh Reddy", "EMPLOYEE", "mfg"),
            ("mfg_eng2@bharti.in", "Meera Nair", "EMPLOYEE", "mfg"),
            ("mfg_op1@bharti.in", "Ramesh Kumar", "EMPLOYEE", "mfg"),
            ("mfg_op2@bharti.in", "Sneha Verma", "EMPLOYEE", "mfg"),

            # Logistics team
            ("log_head@bharti.in", "Harish Gupta", "MANAGER", "logistics"),
            ("log_sup1@bharti.in", "Ashok Yadav", "EMPLOYEE", "logistics"),
            ("log_sup2@bharti.in", "Neha Singh", "EMPLOYEE", "logistics"),
            ("log_op1@bharti.in", "Ajay Kumar", "EMPLOYEE", "logistics"),
            ("log_op2@bharti.in", "Pooja Desai", "EMPLOYEE", "logistics"),

            # R&D team
            ("rnd_head@bharti.in", "Dr. Subodh Joshi", "MANAGER", "rnd"),
            ("rnd_sci1@bharti.in", "Rohit Sharma", "EMPLOYEE", "rnd"),
            ("rnd_sci2@bharti.in", "Shreya Banerjee", "EMPLOYEE", "rnd"),
            ("rnd_eng1@bharti.in", "Nitin Patel", "EMPLOYEE", "rnd"),
            ("rnd_eng2@bharti.in", "Isha Gupta", "EMPLOYEE", "rnd"),

            # Sales team
            ("sales_head@bharti.in", "Vikram Malhotra", "MANAGER", "sales"),
            ("sales_mgr1@bharti.in", "Anand Sharma", "EMPLOYEE", "sales"),
            ("sales_mgr2@bharti.in", "Kavya Rao", "EMPLOYEE", "sales"),
            ("sales_exec1@bharti.in", "Pradeep Kumar", "EMPLOYEE", "sales"),
            ("sales_exec2@bharti.in", "Neeta Chopra", "EMPLOYEE", "sales"),
        ]

        users = {}
        for email, name, role, dept_key in users_data:
            user = User(
                email=email,
                full_name=name,
                password_hash=hash_password("bharti@123"),
                role=UserRole[role],
                department_id=depts[dept_key].id,
                is_active=True,
            )
            db.add(user)
            users[email] = user

        db.flush()

        # Assign managers to departments
        depts["mfg"].manager_id = users["mfg_head@bharti.in"].id
        depts["logistics"].manager_id = users["log_head@bharti.in"].id
        depts["corporate"].manager_id = users["cfo@bharti.in"].id
        depts["rnd"].manager_id = users["rnd_head@bharti.in"].id
        depts["sales"].manager_id = users["sales_head@bharti.in"].id
        db.commit()
        print("✓ 25 users created with manager assignments")

        # =========== 3. CATEGORIES (CSR + CHALLENGE) ===========
        csr_categories = [
            Category(name="Community Development", type=CategoryType.CSR, icon="🏘️"),
            Category(name="Environmental", type=CategoryType.CSR, icon="🌱"),
            Category(name="Education", type=CategoryType.CSR, icon="📚"),
        ]
        challenge_categories = [
            Category(name="Carbon Reduction", type=CategoryType.CHALLENGE, icon="♻️"),
            Category(name="Energy Efficiency", type=CategoryType.CHALLENGE, icon="⚡"),
        ]

        all_categories = csr_categories + challenge_categories
        for cat in all_categories:
            db.add(cat)
        db.flush()
        print("✓ Categories created")

        # =========== 4. EMISSION FACTORS (8v1 + 3v2) ===========
        base_date = date(2025, 1, 1)
        emission_factors = [
            # v1 factors
            EmissionFactor(
                activity_type="Diesel Consumption",
                unit="liters",
                factor_value=Decimal("2.68"),
                source="IPCC AR6",
                version=1,
                valid_from=base_date,
                valid_to=date(2025, 12, 31),
                uncertainty_pct=Decimal("5.2"),
            ),
            EmissionFactor(
                activity_type="Electricity",
                unit="kWh",
                factor_value=Decimal("0.645"),
                source="India Grid Ministry",
                version=1,
                valid_from=base_date,
                valid_to=date(2025, 12, 31),
                uncertainty_pct=Decimal("3.1"),
            ),
            EmissionFactor(
                activity_type="Natural Gas",
                unit="m³",
                factor_value=Decimal("1.96"),
                source="IPCC AR6",
                version=1,
                valid_from=base_date,
                uncertainty_pct=Decimal("4.5"),
            ),
            EmissionFactor(
                activity_type="Gasoline",
                unit="liters",
                factor_value=Decimal("2.31"),
                source="IPCC AR6",
                version=1,
                valid_from=base_date,
                uncertainty_pct=Decimal("5.0"),
            ),
            EmissionFactor(
                activity_type="Aviation Fuel",
                unit="liters",
                factor_value=Decimal("3.16"),
                source="IPCC AR6",
                version=1,
                valid_from=base_date,
                uncertainty_pct=Decimal("6.0"),
            ),
            EmissionFactor(
                activity_type="Train Travel",
                unit="km",
                factor_value=Decimal("0.041"),
                source="IPCC AR6",
                version=1,
                valid_from=base_date,
                uncertainty_pct=Decimal("4.0"),
            ),
            EmissionFactor(
                activity_type="Business Travel (Auto)",
                unit="km",
                factor_value=Decimal("0.211"),
                source="IPCC AR6",
                version=1,
                valid_from=base_date,
                uncertainty_pct=Decimal("5.5"),
            ),
            EmissionFactor(
                activity_type="Purchased Goods",
                unit="INR",
                factor_value=Decimal("0.000058"),
                source="Exiobase 3",
                version=1,
                valid_from=base_date,
                uncertainty_pct=Decimal("8.0"),
            ),
            # v2 revised factors
            EmissionFactor(
                activity_type="Diesel Consumption",
                unit="liters",
                factor_value=Decimal("2.72"),
                source="IPCC AR6 2024",
                version=2,
                valid_from=date(2026, 1, 1),
                uncertainty_pct=Decimal("4.8"),
            ),
            EmissionFactor(
                activity_type="Electricity",
                unit="kWh",
                factor_value=Decimal("0.610"),
                source="India Grid Ministry 2025",
                version=2,
                valid_from=date(2026, 1, 1),
                uncertainty_pct=Decimal("2.8"),
            ),
            EmissionFactor(
                activity_type="Purchased Goods",
                unit="INR",
                factor_value=Decimal("0.000062"),
                source="Exiobase 3.9",
                version=2,
                valid_from=date(2026, 1, 1),
                uncertainty_pct=Decimal("7.5"),
            ),
        ]

        for ef in emission_factors:
            db.add(ef)
        db.flush()
        print("✓ 11 emission factors created (8v1 + 3v2)")

        # =========== 5. OPERATIONAL RECORDS (60 across 3 months) ===========
        op_records = []
        start_date = date(2025, 4, 1)

        # Manufacturing: electricity, diesel
        for i in range(15):
            day = start_date + timedelta(days=2*i)
            op_records.extend([
                OperationalRecord(
                    op_type=OpType.MANUFACTURING,
                    department_id=depts["mfg"].id,
                    activity_type="Electricity",
                    quantity=Decimal(str(2800 + i * 50)),
                    unit="kWh",
                    reference=f"MFG-ELC-{i:03d}",
                    occurred_on=day,
                    created_by=users["mfg_eng1@bharti.in"].id,
                ),
                OperationalRecord(
                    op_type=OpType.MANUFACTURING,
                    department_id=depts["mfg"].id,
                    activity_type="Diesel Consumption",
                    quantity=Decimal(str(450 + i * 10)),
                    unit="liters",
                    reference=f"MFG-DSL-{i:03d}",
                    occurred_on=day,
                    created_by=users["mfg_eng1@bharti.in"].id,
                ),
            ])

        # Logistics: fuel, travel
        for i in range(12):
            day = start_date + timedelta(days=2.5*i)
            op_records.extend([
                OperationalRecord(
                    op_type=OpType.FLEET,
                    department_id=depts["logistics"].id,
                    activity_type="Diesel Consumption",
                    quantity=Decimal(str(800 + i * 25)),
                    unit="liters",
                    reference=f"LOG-FL-{i:03d}",
                    occurred_on=day,
                    created_by=users["log_sup1@bharti.in"].id,
                ),
                OperationalRecord(
                    op_type=OpType.FLEET,
                    department_id=depts["logistics"].id,
                    activity_type="Business Travel (Auto)",
                    quantity=Decimal(str(250 + i * 15)),
                    unit="km",
                    reference=f"LOG-TR-{i:03d}",
                    amount=Decimal(str(8000 + i * 200)),
                    occurred_on=day,
                    created_by=users["log_sup1@bharti.in"].id,
                ),
            ])

        # R&D: electricity, travel
        for i in range(10):
            day = start_date + timedelta(days=3*i)
            op_records.extend([
                OperationalRecord(
                    op_type=OpType.EXPENSE,
                    department_id=depts["rnd"].id,
                    activity_type="Electricity",
                    quantity=Decimal(str(1500 + i * 30)),
                    unit="kWh",
                    reference=f"RND-ELC-{i:03d}",
                    occurred_on=day,
                    created_by=users["rnd_eng1@bharti.in"].id,
                ),
                OperationalRecord(
                    op_type=OpType.PURCHASE,
                    department_id=depts["rnd"].id,
                    activity_type="Purchased Goods",
                    quantity=Decimal("1"),
                    unit="unit",
                    amount=Decimal(str(125000 + i * 2000)),
                    reference=f"RND-PG-{i:03d}",
                    occurred_on=day,
                    created_by=users["rnd_eng1@bharti.in"].id,
                ),
            ])

        # Sales: travel, purchased goods
        for i in range(8):
            day = start_date + timedelta(days=3.75*i)
            op_records.extend([
                OperationalRecord(
                    op_type=OpType.EXPENSE,
                    department_id=depts["sales"].id,
                    activity_type="Business Travel (Auto)",
                    quantity=Decimal(str(180 + i * 20)),
                    unit="km",
                    amount=Decimal(str(5400 + i * 150)),
                    reference=f"SAL-TR-{i:03d}",
                    occurred_on=day,
                    created_by=users["sales_mgr1@bharti.in"].id,
                ),
            ])

        # Corporate: electricity, purchased goods
        for i in range(5):
            day = start_date + timedelta(days=6*i)
            op_records.extend([
                OperationalRecord(
                    op_type=OpType.EXPENSE,
                    department_id=depts["corporate"].id,
                    activity_type="Electricity",
                    quantity=Decimal(str(800 + i * 20)),
                    unit="kWh",
                    reference=f"CRP-ELC-{i:03d}",
                    occurred_on=day,
                    created_by=users["cfo@bharti.in"].id,
                ),
            ])

        for rec in op_records:
            db.add(rec)
        db.flush()
        print(f"✓ {len(op_records)} operational records created")

        # =========== 6. CARBON TRANSACTIONS ===========
        diesel_factor = next(ef for ef in emission_factors if ef.activity_type == "Diesel Consumption" and ef.version == 1)
        electricity_factor = next(ef for ef in emission_factors if ef.activity_type == "Electricity" and ef.version == 1)
        travel_factor = next(ef for ef in emission_factors if ef.activity_type == "Business Travel (Auto)" and ef.version == 1)
        purchased_factor = next(ef for ef in emission_factors if ef.activity_type == "Purchased Goods" and ef.version == 1)

        carbon_txns = []
        for i, rec in enumerate(op_records):
            if rec.activity_type == "Diesel Consumption":
                factor = diesel_factor
                co2e = float(rec.quantity) * 2.68
            elif rec.activity_type == "Electricity":
                factor = electricity_factor
                co2e = float(rec.quantity) * 0.645
            elif rec.activity_type == "Business Travel (Auto)":
                factor = travel_factor
                co2e = float(rec.quantity) * 0.211
            elif rec.activity_type == "Purchased Goods":
                factor = purchased_factor
                co2e = (float(rec.amount) if rec.amount else 0) * 0.000058
            else:
                continue

            carbon_txns.append(
                CarbonTransaction(
                    operational_record_id=rec.id,
                    emission_factor_id=factor.id,
                    factor_value_used=float(factor.factor_value),
                    factor_version_used=factor.version,
                    quantity=float(rec.quantity),
                    co2e_kg=Decimal(str(round(co2e, 2))),
                    scope=1 if rec.department_id else None,
                    data_tier=DataTier.CALCULATED,
                    uncertainty_pct=float(factor.uncertainty_pct) if factor.uncertainty_pct else None,
                    department_id=rec.department_id,
                    occurred_on=rec.occurred_on,
                )
            )

        for txn in carbon_txns:
            db.add(txn)
        db.flush()
        print(f"✓ {len(carbon_txns)} carbon transactions created")

        # =========== 7. ENVIRONMENTAL GOALS ===========
        env_goals = [
            EnvironmentalGoal(
                title="Manufacturing Energy Reduction",
                description="Reduce electricity consumption in manufacturing by 15%",
                metric="electricity_consumption",
                baseline_value=Decimal("3500"),
                target_value=Decimal("2975"),
                current_value=Decimal("3150"),
                unit="kWh/day",
                department_id=depts["mfg"].id,
                start_date=date(2025, 1, 1),
                target_date=date(2025, 12, 31),
                status="ON_TRACK",
            ),
            EnvironmentalGoal(
                title="Logistics Fleet Efficiency",
                description="Reduce diesel consumption by 20% through optimized routes",
                metric="diesel_consumption",
                baseline_value=Decimal("1200"),
                target_value=Decimal("960"),
                current_value=Decimal("980"),
                unit="liters/week",
                department_id=depts["logistics"].id,
                start_date=date(2025, 1, 1),
                target_date=date(2025, 12, 31),
                status="ON_TRACK",
            ),
            EnvironmentalGoal(
                title="Zero Waste Initiative",
                description="Achieve 90% waste recycling across all operations",
                metric="waste_recycling",
                baseline_value=Decimal("65"),
                target_value=Decimal("90"),
                current_value=Decimal("78"),
                unit="% recycled",
                department_id=depts["mfg"].id,
                start_date=date(2025, 1, 1),
                target_date=date(2025, 12, 31),
                status="ON_TRACK",
            ),
            EnvironmentalGoal(
                title="Renewable Energy Transition",
                description="Increase renewable energy usage to 30%",
                metric="renewable_energy",
                baseline_value=Decimal("8"),
                target_value=Decimal("30"),
                current_value=Decimal("14"),
                unit="% of total",
                department_id=None,
                start_date=date(2025, 1, 1),
                target_date=date(2025, 12, 31),
                status="ON_TRACK",
            ),
        ]

        for goal in env_goals:
            db.add(goal)
        db.flush()
        print("✓ 4 environmental goals created")

        # =========== 8. BADGES (6 total) ===========
        badges = [
            Badge(
                name="Carbon Champion",
                description="Reduce personal carbon footprint by 25%",
                icon="🏆",
                tier="GOLD",
                unlock_rule={"type": "carbon_reduction", "target": 25},
                points_value=250,
                is_active=True,
            ),
            Badge(
                name="Energy Saver",
                description="Identify 3 energy efficiency opportunities",
                icon="⚡",
                tier="SILVER",
                unlock_rule={"type": "energy_tips", "count": 3},
                points_value=150,
                is_active=True,
            ),
            Badge(
                name="Green Commuter",
                description="Use public transport 20+ times in a month",
                icon="🚌",
                tier="SILVER",
                unlock_rule={"type": "green_commute", "days": 20},
                points_value=120,
                is_active=True,
            ),
            Badge(
                name="Community Hero",
                description="Participate in 5+ CSR activities",
                icon="🤝",
                tier="GOLD",
                unlock_rule={"type": "csr_participation", "count": 5},
                points_value=200,
                is_active=True,
            ),
            Badge(
                name="Recycling Master",
                description="Complete waste sorting training",
                icon="♻️",
                tier="BRONZE",
                unlock_rule={"type": "training_complete", "training": "waste_sort"},
                points_value=80,
                is_active=True,
            ),
            Badge(
                name="Climate Advocate",
                description="Earn 500+ ESG points",
                icon="🌍",
                tier="PLATINUM",
                unlock_rule={"type": "total_points", "target": 500},
                points_value=300,
                is_active=True,
            ),
        ]

        for badge in badges:
            db.add(badge)
        db.flush()
        print("✓ 6 badges created")

        # =========== 9. REWARDS (5 total) ===========
        rewards = [
            Reward(
                name="Premium Coffee Voucher",
                description="₹500 voucher for cafe chain",
                cost_points=100,
                stock=50,
                image_url="https://via.placeholder.com/200?text=Coffee",
                is_active=True,
            ),
            Reward(
                name="Fitness Band",
                description="Wearable fitness tracker (₹3000 value)",
                cost_points=300,
                stock=10,
                image_url="https://via.placeholder.com/200?text=FitnessBand",
                is_active=True,
            ),
            Reward(
                name="Eco-Friendly Water Bottle",
                description="Bamboo fiber sustainable water bottle",
                cost_points=75,
                stock=100,
                image_url="https://via.placeholder.com/200?text=Bottle",
                is_active=True,
            ),
            Reward(
                name="Annual Leave Bonus",
                description="Extra day of paid leave",
                cost_points=400,
                stock=5,
                image_url="https://via.placeholder.com/200?text=PaidLeave",
                is_active=True,
            ),
            Reward(
                name="Green Workspace Kit",
                description="Desk plants + organic desk organizer",
                cost_points=150,
                stock=20,
                image_url="https://via.placeholder.com/200?text=Workspace",
                is_active=True,
            ),
        ]

        for reward in rewards:
            db.add(reward)
        db.flush()
        print("✓ 5 rewards created")

        # =========== 10. CHALLENGES (5 in mixed lifecycle states) ===========
        today = date.today()
        challenges = [
            Challenge(
                title="May Carbon Reduction Sprint",
                description="Reduce departmental carbon by 10% in May",
                category_id=challenge_categories[0].id,
                lifecycle=ChallengeLifecycle.COMPLETED,
                goal_metric="carbon_reduction_pct",
                goal_target=Decimal("10"),
                points_reward=250,
                badge_id=badges[0].id,
                start_date=date(2025, 5, 1),
                end_date=date(2025, 5, 31),
                created_by=users["ceo@bharti.in"].id,
            ),
            Challenge(
                title="June Energy Audit Challenge",
                description="Participate in facility energy audit",
                category_id=challenge_categories[1].id,
                lifecycle=ChallengeLifecycle.ACTIVE,
                goal_metric="participation",
                goal_target=Decimal("100"),
                points_reward=150,
                badge_id=badges[1].id,
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 30),
                created_by=users["cfo@bharti.in"].id,
            ),
            Challenge(
                title="Sustainable Commute July",
                description="Use green transport 15+ days in July",
                category_id=challenge_categories[1].id,
                lifecycle=ChallengeLifecycle.ACTIVE,
                goal_metric="green_days",
                goal_target=Decimal("15"),
                points_reward=120,
                badge_id=badges[2].id,
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 31),
                created_by=users["csr_head@bharti.in"].id,
            ),
            Challenge(
                title="August Waste Reduction",
                description="Identify waste reduction opportunities",
                category_id=challenge_categories[0].id,
                lifecycle=ChallengeLifecycle.UNDER_REVIEW,
                goal_metric="initiatives",
                goal_target=Decimal("5"),
                points_reward=180,
                badge_id=None,
                start_date=date(2025, 8, 1),
                end_date=date(2025, 8, 31),
                created_by=users["mfg_head@bharti.in"].id,
            ),
            Challenge(
                title="September Green Innovation",
                description="Propose green technology adoption",
                category_id=challenge_categories[1].id,
                lifecycle=ChallengeLifecycle.DRAFT,
                goal_metric="proposals",
                goal_target=Decimal("10"),
                points_reward=200,
                badge_id=badges[5].id,
                start_date=date(2025, 9, 1),
                end_date=date(2025, 9, 30),
                created_by=users["rnd_head@bharti.in"].id,
            ),
        ]

        for challenge in challenges:
            db.add(challenge)
        db.flush()
        print("✓ 5 challenges created (mixed lifecycle)")

        # =========== 11. CHALLENGE PARTICIPATION ===========
        participations = []
        for user_email in ["mfg_eng1@bharti.in", "log_sup1@bharti.in", "rnd_sci1@bharti.in", "sales_mgr1@bharti.in", "corp1@bharti.in"]:
            for ch in challenges[:3]:  # Participate in COMPLETED and ACTIVE challenges
                if ch.lifecycle in (ChallengeLifecycle.COMPLETED, ChallengeLifecycle.ACTIVE):
                    participations.append(
                        ChallengeParticipation(
                            challenge_id=ch.id,
                            user_id=users[user_email].id,
                            progress=Decimal("75") if ch.lifecycle == ChallengeLifecycle.COMPLETED else Decimal("45"),
                            status="COMPLETED" if ch.lifecycle == ChallengeLifecycle.COMPLETED else "JOINED",
                            proof_url="https://example.com/proof" if ch.lifecycle == ChallengeLifecycle.COMPLETED else None,
                            completed_at=ch.end_date if ch.lifecycle == ChallengeLifecycle.COMPLETED else None,
                        )
                    )

        for part in participations:
            db.add(part)
        db.flush()
        print(f"✓ {len(participations)} challenge participations created")

        # =========== 12. CSR ACTIVITIES (4 total) ===========
        csr_activities = [
            CSRActivity(
                title="Tree Plantation Drive - May",
                description="Plant 500 native trees in local watershed",
                category_id=csr_categories[1].id,
                department_id=depts["corporate"].id,
                location="Mulshi, Pune District",
                points_reward=200,
                capacity=50,
                start_date=date(2025, 5, 15),
                end_date=date(2025, 5, 20),
                status="COMPLETED",
                created_by=users["csr_head@bharti.in"].id,
            ),
            CSRActivity(
                title="Adult Literacy Program",
                description="Vocational training for local community",
                category_id=csr_categories[2].id,
                department_id=depts["corporate"].id,
                location="Pimpri-Chinchwad",
                points_reward=150,
                capacity=30,
                start_date=date(2025, 6, 1),
                end_date=date(2025, 8, 31),
                status="ONGOING",
                created_by=users["csr_head@bharti.in"].id,
            ),
            CSRActivity(
                title="Water Conservation Workshop",
                description="Rainwater harvesting setup at schools",
                category_id=csr_categories[1].id,
                department_id=depts["corporate"].id,
                location="Rural villages near Pune",
                points_reward=180,
                capacity=40,
                start_date=date(2025, 6, 15),
                end_date=date(2025, 6, 30),
                status="COMPLETED",
                created_by=users["csr_head@bharti.in"].id,
            ),
            CSRActivity(
                title="Skill Development Initiative",
                description="Training for youth in green jobs",
                category_id=csr_categories[2].id,
                department_id=depts["corporate"].id,
                location="Nigdi, Pune",
                points_reward=250,
                capacity=60,
                start_date=date(2025, 7, 1),
                end_date=date(2025, 9, 30),
                status="OPEN",
                created_by=users["csr_head@bharti.in"].id,
            ),
        ]

        for activity in csr_activities:
            db.add(activity)
        db.flush()
        print("✓ 4 CSR activities created")

        # =========== 13. EMPLOYEE PARTICIPATION IN CSR ===========
        csr_participants = []
        participant_users = [
            "corp1@bharti.in",
            "mfg_eng1@bharti.in",
            "log_sup1@bharti.in",
            "rnd_sci1@bharti.in",
            "sales_mgr1@bharti.in",
            "corp2@bharti.in",
            "mfg_eng2@bharti.in",
            "log_sup2@bharti.in",
        ]

        for i, activity in enumerate(csr_activities):
            for j, user_email in enumerate(participant_users):
                if (i + j) % 2 == 0:  # Alternate participation
                    csr_participants.append(
                        EmployeeParticipation(
                            csr_activity_id=activity.id,
                            user_id=users[user_email].id,
                            status="COMPLETED" if activity.status in ("COMPLETED", "ONGOING") else "REGISTERED",
                            hours=Decimal("8") if activity.status in ("COMPLETED", "ONGOING") else None,
                            verified_by=users["csr_head@bharti.in"].id if activity.status in ("COMPLETED", "ONGOING") else None,
                            verified_at=activity.end_date if activity.status in ("COMPLETED", "ONGOING") else None,
                            proof_url="https://example.com/csr_proof" if activity.status in ("COMPLETED", "ONGOING") else None,
                        )
                    )

        for part in csr_participants:
            db.add(part)
        db.flush()
        print(f"✓ {len(csr_participants)} CSR participations created")

        # =========== 14. USER BADGES ===========
        user_badges = [
            UserBadge(user_id=users["mfg_eng1@bharti.in"].id, badge_id=badges[0].id),
            UserBadge(user_id=users["mfg_eng1@bharti.in"].id, badge_id=badges[2].id),
            UserBadge(user_id=users["log_sup1@bharti.in"].id, badge_id=badges[1].id),
            UserBadge(user_id=users["corp1@bharti.in"].id, badge_id=badges[3].id),
            UserBadge(user_id=users["rnd_sci1@bharti.in"].id, badge_id=badges[4].id),
            UserBadge(user_id=users["sales_mgr1@bharti.in"].id, badge_id=badges[0].id),
        ]

        for ub in user_badges:
            db.add(ub)
        db.flush()
        print("✓ User badges assigned")

        # =========== 15. POINT TRANSACTIONS ===========
        point_txns = [
            PointTransaction(user_id=users["mfg_eng1@bharti.in"].id, points=250, reason="Badge: Carbon Champion"),
            PointTransaction(user_id=users["mfg_eng1@bharti.in"].id, points=100, reason="Challenge completion"),
            PointTransaction(user_id=users["log_sup1@bharti.in"].id, points=150, reason="Badge: Energy Saver"),
            PointTransaction(user_id=users["log_sup1@bharti.in"].id, points=200, reason="CSR activity participation"),
            PointTransaction(user_id=users["corp1@bharti.in"].id, points=200, reason="Badge: Community Hero"),
            PointTransaction(user_id=users["rnd_sci1@bharti.in"].id, points=80, reason="Badge: Recycling Master"),
            PointTransaction(user_id=users["sales_mgr1@bharti.in"].id, points=250, reason="Badge: Carbon Champion"),
            PointTransaction(user_id=users["corp2@bharti.in"].id, points=120, reason="Green commute bonus"),
        ]

        for txn in point_txns:
            db.add(txn)
        db.flush()

        # NOTE: users.points_balance is DEPRECATED and intentionally left at its
        # default (0). Balances are derived from point_transactions via
        # services_features/points.get_balance() — do not write it back here.
        db.commit()
        print("✓ Point transactions created")

        # =========== 16. REWARD REDEMPTIONS ===========
        redemptions = [
            RewardRedemption(
                user_id=users["mfg_eng1@bharti.in"].id,
                reward_id=rewards[2].id,  # Eco-friendly bottle
                points_spent=75,
                status="FULFILLED",
                fulfilled_at=datetime.now(),
            ),
            RewardRedemption(
                user_id=users["log_sup1@bharti.in"].id,
                reward_id=rewards[0].id,  # Coffee voucher
                points_spent=100,
                status="FULFILLED",
                fulfilled_at=datetime.now(),
            ),
            RewardRedemption(
                user_id=users["corp1@bharti.in"].id,
                reward_id=rewards[4].id,  # Workspace kit
                points_spent=150,
                status="PENDING",
            ),
        ]

        for red in redemptions:
            db.add(red)
        db.flush()
        print("✓ Reward redemptions created")

        # =========== 17. ESG POLICIES (3 total) ===========
        policies = [
            ESGPolicy(
                title="Environmental Sustainability Policy",
                body="""
Our commitment to environmental sustainability includes:
- Carbon neutrality by 2030
- 50% renewable energy usage by 2025
- Zero waste to landfill by 2027
- Responsible sourcing of materials
                """,
                version=1,
                category="Environmental",
                is_mandatory=True,
                effective_date=date(2025, 1, 1),
            ),
            ESGPolicy(
                title="Employee Social Responsibility",
                body="""
Guidelines for employee participation in CSR:
- Minimum 16 hours volunteering per year
- Fair wages and benefits
- Safe working conditions
- Non-discrimination and diversity
                """,
                version=1,
                category="Social",
                is_mandatory=True,
                effective_date=date(2025, 1, 1),
            ),
            ESGPolicy(
                title="Governance & Ethics",
                body="""
Code of Conduct and Governance Framework:
- Ethical business practices
- Transparent reporting
- Whistleblower protection
- Board diversity requirements
                """,
                version=2,
                category="Governance",
                is_mandatory=True,
                effective_date=date(2025, 1, 15),
            ),
        ]

        for policy in policies:
            db.add(policy)
        db.flush()
        print("✓ 3 ESG policies created")

        # =========== 18. POLICY ACKNOWLEDGEMENTS (partial) ===========
        # Roughly 65% of employees acknowledge each policy
        ack_users = [
            "mfg_eng1@bharti.in",
            "log_sup1@bharti.in",
            "rnd_sci1@bharti.in",
            "sales_mgr1@bharti.in",
            "corp1@bharti.in",
            "corp2@bharti.in",
            "mfg_eng2@bharti.in",
            "mfg_op1@bharti.in",
            "log_op1@bharti.in",
            "rnd_eng1@bharti.in",
            "sales_mgr2@bharti.in",
            "mfg_op2@bharti.in",
            "log_sup2@bharti.in",
            "rnd_sci2@bharti.in",
            "sales_exec1@bharti.in",
            "sales_exec2@bharti.in",
            "mfg_head@bharti.in",
            "log_head@bharti.in",
        ]

        acks = []
        for policy in policies:
            for user_email in ack_users:
                acks.append(
                    PolicyAcknowledgement(
                        policy_id=policy.id,
                        user_id=users[user_email].id,
                        ip_address="192.168.1.100",
                    )
                )

        for ack in acks:
            db.add(ack)
        db.flush()
        print(f"✓ {len(acks)} policy acknowledgements created")

        # =========== 19. AUDITS (2 total) ===========
        audits = [
            Audit(
                title="GHG Emissions Audit FY2025",
                framework="ISO 14064-1",
                scope="Scope 1 & 2 emissions across all manufacturing facilities",
                status="COMPLETED",
                auditor_user_id=users["cfo@bharti.in"].id,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 5, 31),
                scheduled_date=date(2025, 5, 1),
                completed_date=date(2025, 6, 15),
            ),
            Audit(
                title="ESG Governance Review",
                framework="GRI Standards",
                scope="Policy implementation, reporting, and board oversight",
                status="PLANNED",
                auditor_user_id=users["ceo@bharti.in"].id,
                period_start=date(2025, 7, 1),
                period_end=date(2025, 12, 31),
                scheduled_date=date(2025, 7, 15),
            ),
        ]

        for audit in audits:
            db.add(audit)
        db.flush()
        print("✓ 2 audits created")

        # =========== 20. COMPLIANCE ISSUES (4 total, 1 overdue) ===========
        compliance_issues = [
            ComplianceIssue(
                audit_id=audits[0].id,
                title="Incomplete emission factor documentation",
                description="Source documents missing for 3 electricity factors",
                severity="MEDIUM",
                status="RESOLVED",
                owner_user_id=users["cfo@bharti.in"].id,
                due_date=date(2025, 6, 30),
                resolved_at=datetime.now() - timedelta(days=5),
            ),
            ComplianceIssue(
                audit_id=audits[0].id,
                title="Missing scope 3 data for logistics",
                description="Business travel records incomplete for Q1-Q2",
                severity="HIGH",
                status="OPEN",
                owner_user_id=users["log_head@bharti.in"].id,
                due_date=date(2025, 6, 15),  # OVERDUE
            ),
            ComplianceIssue(
                audit_id=None,
                title="Non-compliant waste disposal",
                description="E-waste disposal not following local regulations",
                severity="HIGH",
                status="OPEN",
                owner_user_id=users["mfg_head@bharti.in"].id,
                due_date=date(2025, 7, 31),
            ),
            ComplianceIssue(
                audit_id=None,
                title="Policy acknowledgement gap",
                description="18% of staff have not acknowledged updated policies",
                severity="MEDIUM",
                status="OPEN",
                owner_user_id=users["csr_head@bharti.in"].id,
                due_date=date(2025, 7, 15),
            ),
        ]

        for issue in compliance_issues:
            db.add(issue)
        db.flush()
        print("✓ 4 compliance issues created (1 overdue)")

        # =========== 21. DEPARTMENT SCORES (70-90 range) ===========
        period_id = "2025-Q2"  # Q2 2025
        dept_scores = [
            DepartmentScore(
                department_id=depts["mfg"].id,
                period=period_id,
                e_score=Decimal("82.5"),
                s_score=Decimal("75.0"),
                g_score=Decimal("78.0"),
                total_score=Decimal("78.5"),
            ),
            DepartmentScore(
                department_id=depts["logistics"].id,
                period=period_id,
                e_score=Decimal("79.0"),
                s_score=Decimal("80.5"),
                g_score=Decimal("76.0"),
                total_score=Decimal("78.5"),
            ),
            DepartmentScore(
                department_id=depts["corporate"].id,
                period=period_id,
                e_score=Decimal("75.0"),
                s_score=Decimal("88.0"),
                g_score=Decimal("89.0"),
                total_score=Decimal("84.0"),
            ),
            DepartmentScore(
                department_id=depts["rnd"].id,
                period=period_id,
                e_score=Decimal("85.0"),
                s_score=Decimal("76.5"),
                g_score=Decimal("74.0"),
                total_score=Decimal("78.5"),
            ),
            DepartmentScore(
                department_id=depts["sales"].id,
                period=period_id,
                e_score=Decimal("72.0"),
                s_score=Decimal("82.0"),
                g_score=Decimal("81.0"),
                total_score=Decimal("78.3"),
            ),
        ]

        for score in dept_scores:
            db.add(score)
        db.flush()
        print("✓ Department scores created (70-90 range)")

        # =========== 22. SETTINGS ===========
        from app.models.misc import Settings
        settings = Settings(
            gamification_enabled=True,
            csr_module_enabled=True,
            notifications_enabled=True,
            public_leaderboard=True,
            esg_weights={"E": 40, "S": 30, "G": 30},
        )
        db.add(settings)
        db.flush()
        print("✓ Settings created")

        # Final commit
        db.commit()
        print("\n✅ Seed data loaded successfully!\n")
        print("Summary:")
        print(f"  • Departments: 5 (+ 1 root)")
        print(f"  • Users: 25")
        print(f"  • Emission Factors: 11 (8v1 + 3v2)")
        print(f"  • Operational Records: {len(op_records)}")
        print(f"  • Carbon Transactions: {len(carbon_txns)}")
        print(f"  • Environmental Goals: 4")
        print(f"  • Badges: 6")
        print(f"  • Rewards: 5")
        print(f"  • Challenges: 5 (mixed lifecycle)")
        print(f"  • CSR Activities: 4")
        print(f"  • Policies: 3 (with {len(acks)} partial acks)")
        print(f"  • Audits: 2")
        print(f"  • Compliance Issues: 4 (1 overdue)")
        print(f"  • Department Scores: 5 (E/S/G ~70-90)")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
