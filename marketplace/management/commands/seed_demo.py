from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from marketplace.ai import analyze_text, detect_fraud, predict_fair_price
from marketplace.models import Favorite, Listing, Message, Notification, Payment, Review


class Command(BaseCommand):
    help = "Create repeatable demo students, listings and interactions."

    def handle(self, *args, **options):
        students = [
            {
                "username": "saiteja",
                "password": "Campus@123",
                "first_name": "Sai Teja",
                "email": "saiteja@mvsrec.edu.in",
                "course": "Information Technology",
                "year": "4th Year",
                "interests": ["Python", "machine learning", "engineering books", "electronics"],
                "staff": False,
            },
            {
                "username": "ananya",
                "password": "Campus@123",
                "first_name": "Ananya",
                "email": "ananya@mvsrec.edu.in",
                "course": "Computer Science",
                "year": "3rd Year",
                "interests": ["data structures", "design", "books"],
                "staff": False,
            },
            {
                "username": "rahul",
                "password": "Campus@123",
                "first_name": "Rahul",
                "email": "rahul@mvsrec.edu.in",
                "course": "Electronics and Communication",
                "year": "4th Year",
                "interests": ["calculator", "lab equipment", "electronics"],
                "staff": False,
            },
            {
                "username": "admin",
                "password": "Admin@123",
                "first_name": "Campus Admin",
                "email": "admin@mvsrec.edu.in",
                "course": "Student Services",
                "year": "Staff",
                "interests": ["safety", "moderation"],
                "staff": True,
            },
        ]
        users = {}
        for data in students:
            user, _ = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "email": data["email"],
                    "is_staff": data["staff"],
                    "is_superuser": data["staff"],
                },
            )
            user.first_name = data["first_name"]
            user.email = data["email"]
            user.is_staff = data["staff"]
            user.is_superuser = data["staff"]
            user.set_password(data["password"])
            user.save()
            user.profile.course = data["course"]
            user.profile.year = data["year"]
            user.profile.interests = data["interests"]
            user.profile.email_verified = True
            user.profile.trust_score = 96 if data["staff"] else 88
            user.profile.points = 460 if user.username == "saiteja" else 220
            user.profile.save()
            users[user.username] = user

        sample_listings = [
            {
                "id": "booksdsa2026",
                "seller": "ananya",
                "title": "Data Structures & Algorithms Textbook Set",
                "description": "Two clean reference books with highlighted examples, interview problems and handwritten shortcut notes. Ideal for IT and CSE students preparing for placements.",
                "category": "books",
                "condition": "good",
                "transaction_type": "sell",
                "price": 560,
                "location": "Library Block",
                "course_tags": "IT, CSE, DSA, placements",
                "image_url": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=1000&q=80",
                "demand": 84,
                "quality": 86,
            },
            {
                "id": "calcsci2026a",
                "seller": "rahul",
                "title": "Casio Scientific Calculator FX-991ES",
                "description": "Fully working scientific calculator with protective cover. All keys and display tested. Useful for engineering mathematics and lab calculations.",
                "category": "electronics",
                "condition": "like_new",
                "transaction_type": "sell",
                "price": 780,
                "location": "ECE Block",
                "course_tags": "Engineering Maths, ECE, Mechanical",
                "image_url": "https://yamada-denkiweb-media.com/wp-content/uploads/2025/07/AdobeStock_439933359-scaled.jpeg",
                "demand": 89,
                "quality": 90,
            },
            {
                "id": "laptop2026a",
                "seller": "rahul",
                "title": "Student Laptop — 8GB RAM, 512GB SSD",
                "description": "Reliable laptop for Python, web development and assignments. Fresh installation, good battery backup and original charger included.",
                "category": "electronics",
                "condition": "good",
                "transaction_type": "sell",
                "price": 18500,
                "location": "Main Canteen",
                "course_tags": "Python, coding, projects",
                "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1000&q=80",
                "demand": 92,
                "quality": 81,
            },
            {
                "id": "coatlab2026",
                "seller": "ananya",
                "title": "White Lab Coat — Medium",
                "description": "Washed and neatly maintained lab coat suitable for chemistry and workshop sessions. Available for short-term borrowing this semester.",
                "category": "lab",
                "condition": "good",
                "transaction_type": "borrow",
                "price": 0,
                "location": "Science Block",
                "course_tags": "Lab, chemistry, workshop",
                "image_url": "https://images.unsplash.com/photo-1584982751601-97dcc096659c?auto=format&fit=crop&w=1000&q=80",
                "demand": 58,
                "quality": 78,
            },
            {
                "id": "bagcamp2026",
                "seller": "saiteja",
                "title": "Water-Resistant College Backpack",
                "description": "Comfortable navy backpack with laptop sleeve, bottle pockets and strong zippers. Cleaned and ready for daily campus use.",
                "category": "hostel",
                "condition": "like_new",
                "transaction_type": "sell",
                "price": 900,
                "location": "IT Block",
                "course_tags": "Backpack, laptop, college",
                "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=1000&q=80",
                "demand": 69,
                "quality": 88,
            },
            {
                "id": "cycle2026aa",
                "seller": "rahul",
                "title": "Campus Bicycle — Monthly Rental",
                "description": "Well-maintained single-speed bicycle with lock. Best for hostel students commuting around campus and nearby areas.",
                "category": "sports",
                "condition": "good",
                "transaction_type": "rent",
                "price": 650,
                "location": "Boys Hostel Gate",
                "course_tags": "Cycle, commute, hostel",
                "image_url": "https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=1000&q=80",
                "demand": 74,
                "quality": 76,
            },
            {
                "id": "headphones26",
                "seller": "saiteja",
                "title": "Wired Over-Ear Headphones",
                "description": "Clear audio and comfortable ear cushions. Works well for online classes, coding sessions and music in the hostel.",
                "category": "electronics",
                "condition": "good",
                "transaction_type": "sell",
                "price": 700,
                "location": "IT Block",
                "course_tags": "Audio, classes, hostel",
                "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1000&q=80",
                "demand": 66,
                "quality": 82,
            },
            {
                "id": "pythonbook26",
                "seller": "ananya",
                "title": "Python Machine Learning Handbook",
                "description": "Beginner-friendly ML handbook covering NumPy, pandas, scikit-learn, model evaluation and practical mini projects.",
                "category": "books",
                "condition": "like_new",
                "transaction_type": "sell",
                "price": 620,
                "location": "Central Library",
                "course_tags": "Python, ML, AI, scikit-learn",
                "image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=1000&q=80",
                "demand": 91,
                "quality": 91,
            },
            {
                "id": "badminton026",
                "seller": "rahul",
                "title": "Badminton Racket Pair",
                "description": "Two lightweight rackets in good playing condition with one shuttle tube. Suitable for evening recreation on campus.",
                "category": "sports",
                "condition": "good",
                "transaction_type": "rent",
                "price": 150,
                "location": "Sports Complex",
                "course_tags": "Badminton, sports, recreation",
                "image_url": "https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=1000&q=80",
                "demand": 60,
                "quality": 75,
            },
            {
                "id": "notebook2026",
                "seller": "saiteja",
                "title": "Unused A4 Notebooks — Set of Three",
                "description": "Three new ruled notebooks available as a donation for a student who needs them this semester. Campus pickup only.",
                "category": "other",
                "condition": "new",
                "transaction_type": "donate",
                "price": 0,
                "location": "Admin Block",
                "course_tags": "Stationery, notes, donation",
                "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?auto=format&fit=crop&w=1000&q=80",
                "demand": 77,
                "quality": 93,
            },
        ]

        created_listings = {}
        for row in sample_listings:
            prediction = predict_fair_price(
                row["category"], row["condition"], row["transaction_type"], row["demand"], row["quality"]
            )
            fraud = detect_fraud(
                row["title"], row["description"], row["price"], prediction["price"]
            )
            listing, _ = Listing.objects.update_or_create(
                id=row["id"],
                defaults={
                    "seller": users[row["seller"]],
                    "title": row["title"],
                    "description": row["description"],
                    "category": row["category"],
                    "condition": row["condition"],
                    "transaction_type": row["transaction_type"],
                    "price": Decimal(str(row["price"])),
                    "predicted_price": Decimal(str(prediction["price"])),
                    "location": row["location"],
                    "course_tags": row["course_tags"],
                    "image_url": row["image_url"],
                    "demand_score": row["demand"],
                    "image_quality_score": row["quality"],
                    "fraud_score": fraud["score"],
                    "fraud_reasons": fraud["reasons"],
                    "moderation_status": "approved",
                    "status": "active",
                    "views": row["demand"] * 2,
                },
            )
            created_listings[row["id"]] = listing

        Favorite.objects.get_or_create(user=users["saiteja"], listing=created_listings["pythonbook26"])
        Favorite.objects.get_or_create(user=users["saiteja"], listing=created_listings["calcsci2026a"])

        text_result = analyze_text("Is the DSA set available? I can collect it after class tomorrow.")
        Message.objects.get_or_create(
            id="msgdemo00001",
            defaults={
                "listing": created_listings["booksdsa2026"],
                "sender": users["saiteja"],
                "receiver": users["ananya"],
                "body": "Is the DSA set available? I can collect it after class tomorrow.",
                "sentiment": text_result["sentiment"],
            },
        )
        Message.objects.get_or_create(
            id="msgdemo00002",
            defaults={
                "listing": created_listings["booksdsa2026"],
                "sender": users["ananya"],
                "receiver": users["saiteja"],
                "body": "Yes, it is available. The library entrance at 3 PM works for me.",
                "sentiment": "positive",
            },
        )

        Payment.objects.get_or_create(
            transaction_ref="DEMO-CAMPUS-001",
            defaults={
                "listing": created_listings["headphones26"],
                "buyer": users["ananya"],
                "amount": Decimal("700"),
                "method": "upi",
                "status": "captured",
            },
        )
        Review.objects.update_or_create(
            listing=created_listings["headphones26"],
            author=users["ananya"],
            defaults={
                "seller": users["saiteja"],
                "rating": 5,
                "body": "Clean product, fair price and smooth campus pickup.",
                "sentiment": "positive",
                "moderation_status": "approved",
            },
        )
        Notification.objects.get_or_create(
            user=users["saiteja"],
            title="Your recommendations are ready",
            defaults={
                "body": "Python ML ranked new books and electronics using your IT and machine-learning interests.",
                "kind": "ai",
            },
        )
        self.stdout.write(self.style.SUCCESS("Demo data created. Login: saiteja / Campus@123"))
