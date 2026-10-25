from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from shop.models import Activity, Category, StudentProfile, Trainer, TrainerProfile


class Command(BaseCommand):
    help = 'Create or update realistic sample data for the activities portal.'

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()

        category_data = {
            'Web Development': 'Build practical skills for creating modern websites.',
            'Python Programming': 'Develop a strong foundation in Python programming.',
            'Artificial Intelligence': 'Explore the ideas and tools behind intelligent systems.',
            'Data Science': 'Learn how to work with data and communicate useful findings.',
            'Database': 'Understand how structured data is stored, queried, and maintained.',
            'React Development': 'Create responsive interfaces with a component-based approach.',
            'UI/UX Design': 'Design digital experiences that are clear, useful, and inclusive.',
            'Cybersecurity': 'Learn practical principles for protecting applications and users.',
        }
        category_aliases = {
            'Artificial Intelligence': 'AI and Robotics',
        }
        categories = {}
        for name, description in category_data.items():
            category = Category.objects.filter(name=name).first()
            if category is None:
                alias = category_aliases.get(name)
                category = Category.objects.filter(name=alias).first() if alias else None
                if category is not None:
                    category.name = name
            if category is None:
                category = Category(name=name)
            category.description = description
            category.save()
            categories[name] = category

        trainer_data = [
            {
                'email': 'alice.morgan@university.edu',
                'full_name': 'د. أحمد حسن',
                'phone_number': '+1 555 0101',
                'professional_title': 'Senior Lecturer in Computing',
                'specialization': 'Web technologies and software engineering',
                'years_of_experience': 9,
            },
            {
                'email': 'daniel.lee@university.edu',
                'full_name': 'محمد خالد',
                'phone_number': '+1 555 0102',
                'professional_title': 'Python Developer and Teaching Fellow',
                'specialization': 'Python programming and data analysis',
                'years_of_experience': 7,
            },
            {
                'email': 'maya.patel@university.edu',
                'full_name': 'د. عمر محمود',
                'phone_number': '+1 555 0103',
                'professional_title': 'Research Fellow in Artificial Intelligence',
                'specialization': 'Machine learning and responsible AI',
                'years_of_experience': 8,
            },
            {
                'email': 'jonathan.reed@university.edu',
                'full_name': 'يوسف إبراهيم',
                'phone_number': '+1 555 0104',
                'professional_title': 'UX Designer and Visiting Tutor',
                'specialization': 'User research and interface design',
                'years_of_experience': 6,
            },
            {
                'email': 'sarah.okafor@university.edu',
                'full_name': 'عبد الرحمن علي',
                'phone_number': '+1 555 0105',
                'professional_title': 'Cybersecurity Consultant',
                'specialization': 'Application security and digital safety',
                'years_of_experience': 10,
            },
        ]
        trainers = {}
        for data in trainer_data:
            existing_trainer = Trainer.objects.filter(email='alice@example.com').first() if data['full_name'] == 'د. أحمد حسن' else None
            if existing_trainer is not None:
                trainer = existing_trainer
                trainer.email = data['email']
                trainer.full_name = data['full_name']
                trainer.phone_number = data['phone_number']
                trainer.save()
            else:
                trainer, _ = Trainer.objects.update_or_create(
                    email=data['email'],
                    defaults={
                        'full_name': data['full_name'],
                        'phone_number': data['phone_number'],
                    },
                )
            TrainerProfile.objects.update_or_create(
                trainer=trainer,
                defaults={
                    'professional_title': data['professional_title'],
                    'specialization': data['specialization'],
                    'years_of_experience': data['years_of_experience'],
                },
            )
            trainers[data['full_name']] = trainer

        activity_data = [
            {
                'title': 'Introduction to Web Development',
                'category': 'Web Development',
                'trainer': 'د. أحمد حسن',
                'days_from_today': 7,
                'duration': 6,
                'max_students': 24,
                'available': True,
                'short': 'Learn the building blocks of websites through a guided practical project.',
                'full': 'This introductory workshop covers the structure of web pages, basic styling, and the role of a browser. Students finish with a small, accessible multi-page site.',
                'outcomes': 'Explain how browsers request and display web pages.\nCreate a semantic multi-page website.\nApply basic responsive layout and accessibility practices.',
                'prerequisites': 'No previous web development experience required. Bring a laptop with a modern browser.',
                'level': 'beginner',
            },
            {
                'title': 'HTML & CSS Fundamentals',
                'category': 'Web Development',
                'trainer': 'د. أحمد حسن',
                'days_from_today': -8,
                'duration': 4,
                'max_students': 20,
                'available': True,
                'short': 'Build a solid foundation in semantic HTML and responsive CSS.',
                'full': 'Students practise semantic markup, layout fundamentals, typography, and responsive design while creating a polished university event page.',
                'outcomes': 'Structure content with semantic HTML elements.\nUse CSS selectors, spacing, and typography effectively.\nBuild a page that adapts to smaller screens.',
                'prerequisites': 'Comfort using a web browser and basic file management. No coding experience required.',
                'level': 'beginner',
            },
            {
                'title': 'Python Programming Basics',
                'category': 'Python Programming',
                'trainer': 'محمد خالد',
                'days_from_today': 14,
                'duration': 7,
                'max_students': 25,
                'available': True,
                'short': 'Start writing clear Python programs with guided exercises.',
                'full': 'A beginner-friendly introduction to variables, conditions, loops, functions, and simple data structures, with short exercises throughout the week.',
                'outcomes': 'Write Python programs using variables and control flow.\nCreate reusable functions with clear parameters.\nWork with lists, dictionaries, and simple input data.',
                'prerequisites': 'No previous programming experience required.',
                'level': 'beginner',
            },
            {
                'title': 'Python OOP Workshop',
                'category': 'Python Programming',
                'trainer': 'محمد خالد',
                'days_from_today': -18,
                'duration': 3,
                'max_students': 18,
                'available': False,
                'short': 'Practise object-oriented design in small, understandable Python projects.',
                'full': 'This workshop introduces classes, objects, inheritance, and composition through a small project that students can extend after the session.',
                'outcomes': 'Design classes with meaningful attributes and methods.\nUse composition and inheritance appropriately.\nOrganise a small Python project into maintainable objects.',
                'prerequisites': 'Basic Python syntax, functions, lists, and dictionaries.',
                'level': 'intermediate',
            },
            {
                'title': 'Introduction to Artificial Intelligence',
                'category': 'Artificial Intelligence',
                'trainer': 'د. عمر محمود',
                'days_from_today': 21,
                'duration': 5,
                'max_students': 22,
                'available': True,
                'short': 'Understand the main ideas, uses, and responsibilities of modern AI.',
                'full': 'Students explore how intelligent systems are built, where machine learning fits, and why responsible use matters in real university and workplace contexts.',
                'outcomes': 'Distinguish artificial intelligence, machine learning, and automation.\nDescribe how data supports an intelligent system.\nIdentify important fairness, privacy, and accountability questions.',
                'prerequisites': 'No previous AI experience required. General computer literacy is helpful.',
                'level': 'beginner',
            },
            {
                'title': 'Machine Learning Fundamentals',
                'category': 'Artificial Intelligence',
                'trainer': 'د. عمر محمود',
                'days_from_today': -12,
                'duration': 8,
                'max_students': 20,
                'available': False,
                'short': 'Explore supervised learning concepts with approachable examples.',
                'full': 'A practical introduction to datasets, features, training, evaluation, and common machine learning workflows using small, interpretable examples.',
                'outcomes': 'Prepare a small dataset for supervised learning.\nCompare training and evaluation data.\nInterpret basic model performance measures and limitations.',
                'prerequisites': 'Basic Python and familiarity with descriptive statistics or spreadsheets.',
                'level': 'intermediate',
            },
            {
                'title': 'Data Analysis with Python',
                'category': 'Data Science',
                'trainer': 'محمد خالد',
                'days_from_today': 28,
                'duration': 6,
                'max_students': 24,
                'available': True,
                'short': 'Turn a raw dataset into clear findings and useful visual summaries.',
                'full': 'Students work through a small analysis project covering data cleaning, exploration, basic visualisation, and communicating conclusions responsibly.',
                'outcomes': 'Clean and inspect a small tabular dataset.\nSummarise patterns with suitable visualisations.\nPresent evidence-based findings clearly.',
                'prerequisites': 'Basic Python programming or equivalent experience working with spreadsheets.',
                'level': 'intermediate',
            },
            {
                'title': 'SQL & Database Fundamentals',
                'category': 'Database',
                'trainer': 'د. أحمد حسن',
                'days_from_today': -4,
                'duration': 4,
                'max_students': 20,
                'available': True,
                'short': 'Learn how to query and organise structured information with SQL.',
                'full': 'This activity covers tables, relationships, filtering, joins, and practical query writing using a small university data example.',
                'outcomes': 'Write SELECT queries with filtering and sorting.\nConnect related tables with joins.\nExplain how keys and relationships organise data.',
                'prerequisites': 'No database experience required. Basic computer literacy is sufficient.',
                'level': 'beginner',
            },
            {
                'title': 'React.js Fundamentals',
                'category': 'React Development',
                'trainer': 'د. أحمد حسن',
                'days_from_today': 35,
                'duration': 7,
                'max_students': 18,
                'available': True,
                'short': 'Learn the component mindset behind modern interactive interfaces.',
                'full': 'Students learn the basic structure of a React application, reusable components, props, and state through a focused interface project.',
                'outcomes': 'Build reusable React components.\nPass data with props and manage simple state.\nOrganise a small interface into clear component responsibilities.',
                'prerequisites': 'HTML, CSS, and basic JavaScript familiarity.',
                'level': 'intermediate',
            },
            {
                'title': 'Building Modern User Interfaces',
                'category': 'UI/UX Design',
                'trainer': 'يوسف إبراهيم',
                'days_from_today': -25,
                'duration': 5,
                'max_students': 16,
                'available': False,
                'short': 'Shape a clear interface from an idea into a practical screen design.',
                'full': 'Students move from simple user needs to wireframes and a polished interface, learning how spacing, hierarchy, and content support usability.',
                'outcomes': 'Translate a user need into a simple interface structure.\nCreate low-fidelity wireframes.\nUse hierarchy, spacing, and content to improve usability.',
                'prerequisites': 'No design software experience required. Curiosity about how people use digital products is helpful.',
                'level': 'beginner',
            },
            {
                'title': 'UI/UX Design Fundamentals',
                'category': 'UI/UX Design',
                'trainer': 'يوسف إبراهيم',
                'days_from_today': 42,
                'duration': 4,
                'max_students': 16,
                'available': True,
                'short': 'Learn the principles of user-centred design through practical exercises.',
                'full': 'An accessible introduction to user research, information hierarchy, prototyping, and inclusive design decisions for digital products.',
                'outcomes': 'Plan a small user research activity.\nOrganise information into a clear content hierarchy.\nCreate and review a simple accessible prototype.',
                'prerequisites': 'Basic familiarity with websites or mobile applications.',
                'level': 'intermediate',
            },
            {
                'title': 'Web Security Basics',
                'category': 'Cybersecurity',
                'trainer': 'عبد الرحمن علي',
                'days_from_today': 49,
                'duration': 3,
                'max_students': 20,
                'available': True,
                'short': 'Understand common web risks and the habits that help prevent them.',
                'full': 'Students learn the principles behind secure passwords, input validation, access control, and common web vulnerabilities in a safe educational setting.',
                'outcomes': 'Explain why authentication and access control are different.\nRecognise common input validation risks.\nApply basic secure development habits to a web feature.',
                'prerequisites': 'Basic web development knowledge is recommended. This is a defensive, educational workshop.',
                'level': 'intermediate',
            },
        ]

        for data in activity_data:
            Activity.objects.update_or_create(
                title=data['title'],
                defaults={
                    'short_description': data['short'],
                    'full_description': data['full'],
                    'learning_outcomes': data['outcomes'],
                    'prerequisites': data['prerequisites'],
                    'level': data['level'],
                    'category': categories[data['category']],
                    'trainer': trainers[data['trainer']],
                    'start_date': today + timedelta(days=data['days_from_today']),
                    'duration': data['duration'],
                    'max_students': data['max_students'],
                    'availability_status': data['available'],
                },
            )

        legacy_content = {
            'Python Bootcamp': {
                'short_description': 'Build confidence with Python through practical programming challenges.',
                'full_description': 'This hands-on bootcamp introduces Python syntax, problem-solving, and common data structures through a series of short exercises that build toward a small command-line project.',
                'learning_outcomes': 'Write readable Python using variables, conditions, and loops.\nBreak a problem into functions and test each part.\nChoose suitable lists, dictionaries, or sets for simple tasks.',
                'prerequisites': 'No previous programming experience required.',
                'level': 'beginner',
            },
            'Robotics Lab': {
                'short_description': 'Explore how sensors, code, and simple mechanisms work together in a guided lab.',
                'full_description': 'Students investigate the foundations of educational robotics by assembling a small system, reading sensor input, and programming a repeatable movement sequence in a supervised lab environment.',
                'learning_outcomes': 'Explain how a sensor provides input to a robotic system.\nWrite a simple program that responds to sensor readings.\nTest and improve a repeatable movement sequence.',
                'prerequisites': 'No robotics experience required. Comfortable following a practical lab procedure.',
                'level': 'beginner',
            },
        }
        for title, content in legacy_content.items():
            Activity.objects.filter(title=title).update(**content)

        student_data = [
            {
                'username': 'student_ahmed', 'first_name': 'Ahmed', 'last_name': 'Mahmoud',
                'email': 'student.ahmed@example.com', 'phone_number': '01000000001',
                'faculty': 'Computers and Artificial Intelligence', 'academic_year': 'Third year',
            },
            {
                'username': 'student_omar', 'first_name': 'Omar', 'last_name': 'Hassan',
                'email': 'student.omar@example.com', 'phone_number': '01000000002',
                'faculty': 'Engineering', 'academic_year': 'Second year',
            },
            {
                'username': 'student_youssef', 'first_name': 'Youssef', 'last_name': 'Ali',
                'email': 'student.youssef@example.com', 'phone_number': '01000000003',
                'faculty': 'Commerce', 'academic_year': 'Fourth year',
            },
            {
                'username': 'student_mohamed', 'first_name': 'Mohamed', 'last_name': 'Ibrahim',
                'email': 'student.mohamed@example.com', 'phone_number': '01000000004',
                'faculty': 'Science', 'academic_year': 'First year',
            },
        ]
        demo_password = 'StudentDemo123!'
        for data in student_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': data['email'],
                },
            )
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.email = data['email']
            if created or not user.has_usable_password():
                user.set_password(demo_password)
            user.save()
            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone_number': data['phone_number'],
                    'university': 'Beni-Suef University',
                    'faculty': data['faculty'],
                    'academic_year': data['academic_year'],
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f'Sample data ready: {Category.objects.count()} categories, '
            f'{Trainer.objects.count()} trainers, {Activity.objects.count()} activities, '
            f'{StudentProfile.objects.count()} student profiles.'
        ))
