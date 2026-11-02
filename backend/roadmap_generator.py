"""
Roadmap Generator — creates personalized learning roadmaps based on skill gaps
"""
import json
from typing import List, Dict, Any


# ─── Learning resource database ──────────────────────────────────────────────

SKILL_ROADMAP_DB = {
    'Python': {
        'priority': 'high',
        'duration': '4-6 weeks',
        'stages': {
            'learn': {
                'topics': ['Variables, data types, control flow', 'Functions & modules', 'OOP concepts', 'File I/O', 'Libraries: os, sys, re'],
                'resources': [
                    {'name': 'Python.org Official Tutorial', 'url': 'https://docs.python.org/3/tutorial/', 'free': True},
                    {'name': 'CS50P - Python for Beginners', 'url': 'https://cs50.harvard.edu/python/', 'free': True},
                    {'name': 'Automate the Boring Stuff', 'url': 'https://automatetheboringstuff.com/', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Solve 20 HackerRank Python challenges', 'Build a CLI tool', 'Write OOP-based application'],
                'platforms': ['HackerRank', 'LeetCode', 'Exercism'],
            },
            'build': {
                'projects': ['To-do CLI app', 'Web scraper', 'Simple REST API with Flask'],
            },
            'apply': {
                'actions': ['Add Python to resume', 'Push projects to GitHub', 'Apply to Python internships/jobs'],
            },
        },
    },
    'React': {
        'priority': 'high',
        'duration': '4-6 weeks',
        'stages': {
            'learn': {
                'topics': ['JSX & components', 'Props & state', 'Hooks (useState, useEffect)', 'React Router', 'Context API'],
                'resources': [
                    {'name': 'React Official Docs', 'url': 'https://react.dev/learn', 'free': True},
                    {'name': 'Full Stack Open (React)', 'url': 'https://fullstackopen.com/', 'free': True},
                    {'name': 'The Odin Project', 'url': 'https://www.theodinproject.com/', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Build counter and form apps', 'Fetch & display API data', 'Build a todo app with hooks'],
                'platforms': ['Frontend Mentor', 'CodeSandbox', 'StackBlitz'],
            },
            'build': {
                'projects': ['Weather app using public API', 'E-commerce product listing', 'Portfolio website'],
            },
            'apply': {
                'actions': ['Deploy to Vercel/Netlify', 'Add to portfolio', 'Contribute to React open source'],
            },
        },
    },
    'SQL': {
        'priority': 'high',
        'duration': '2-3 weeks',
        'stages': {
            'learn': {
                'topics': ['SELECT, INSERT, UPDATE, DELETE', 'JOINs (INNER, LEFT, RIGHT)', 'GROUP BY, ORDER BY', 'Subqueries', 'Indexes & optimization'],
                'resources': [
                    {'name': 'SQLZoo', 'url': 'https://sqlzoo.net/', 'free': True},
                    {'name': 'Mode Analytics SQL Tutorial', 'url': 'https://mode.com/sql-tutorial/', 'free': True},
                    {'name': 'W3Schools SQL', 'url': 'https://www.w3schools.com/sql/', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Complete SQLZoo exercises', 'Write 30 queries on sample datasets', 'Optimize slow queries'],
                'platforms': ['SQLZoo', 'LeetCode Database', 'HackerRank SQL'],
            },
            'build': {
                'projects': ['Student management DB', 'E-commerce DB schema', 'Analytics dashboard queries'],
            },
            'apply': {
                'actions': ['Mention SQL in skills section', 'Add database project to GitHub', 'Practice SQL interviews'],
            },
        },
    },
    'Machine Learning': {
        'priority': 'high',
        'duration': '8-12 weeks',
        'stages': {
            'learn': {
                'topics': ['Supervised vs unsupervised learning', 'Regression & classification', 'Model evaluation metrics', 'Feature engineering', 'Model selection'],
                'resources': [
                    {'name': 'fast.ai Practical ML', 'url': 'https://course.fast.ai/', 'free': True},
                    {'name': 'Google ML Crash Course', 'url': 'https://developers.google.com/machine-learning/crash-course', 'free': True},
                    {'name': 'Kaggle Learn', 'url': 'https://www.kaggle.com/learn', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Titanic survival prediction', 'House price regression', 'MNIST digit classification'],
                'platforms': ['Kaggle', 'Google Colab', 'Papers With Code'],
            },
            'build': {
                'projects': ['Spam email classifier', 'Customer churn prediction', 'Recommendation system'],
            },
            'apply': {
                'actions': ['Create Kaggle profile', 'Write blog post on project', 'Apply to ML internships'],
            },
        },
    },
    'Docker': {
        'priority': 'medium',
        'duration': '1-2 weeks',
        'stages': {
            'learn': {
                'topics': ['Containers vs VMs', 'Dockerfile syntax', 'docker run, build, push', 'Docker Compose', 'Networking & volumes'],
                'resources': [
                    {'name': 'Docker Official Get Started', 'url': 'https://docs.docker.com/get-started/', 'free': True},
                    {'name': 'Play with Docker', 'url': 'https://labs.play-with-docker.com/', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Containerize a Python app', 'Multi-service docker-compose setup', 'Push image to Docker Hub'],
                'platforms': ['Play with Docker', 'KodeKloud', 'Docker Hub'],
            },
            'build': {
                'projects': ['Dockerized Flask app', 'Multi-container web app with Compose'],
            },
            'apply': {
                'actions': ['Add Docker to skills', 'Include Docker in projects', 'Get Docker Certified Associate'],
            },
        },
    },
    'AWS': {
        'priority': 'medium',
        'duration': '4-6 weeks',
        'stages': {
            'learn': {
                'topics': ['Core services: EC2, S3, RDS, Lambda', 'IAM & security', 'VPC & networking', 'Serverless architecture', 'Cost management'],
                'resources': [
                    {'name': 'AWS Free Tier', 'url': 'https://aws.amazon.com/free/', 'free': True},
                    {'name': 'AWS Skill Builder', 'url': 'https://skillbuilder.aws/', 'free': True},
                    {'name': 'A Cloud Guru (Cloud Foundations)', 'url': 'https://acloudguru.com/', 'free': False},
                ],
            },
            'practice': {
                'exercises': ['Host static site on S3', 'Deploy EC2 instance', 'Create Lambda function'],
                'platforms': ['AWS Free Tier', 'CloudQuest', 'Qwiklabs'],
            },
            'build': {
                'projects': ['Serverless API with Lambda + API Gateway', 'Static website on S3 + CloudFront'],
            },
            'apply': {
                'actions': ['Get AWS Cloud Practitioner certification', 'Add AWS to resume', 'Build cloud portfolio'],
            },
        },
    },
    'Git': {
        'priority': 'high',
        'duration': '1 week',
        'stages': {
            'learn': {
                'topics': ['git init, add, commit', 'Branching & merging', 'Remote repos (push, pull, fetch)', 'Pull requests & code review', 'Resolving conflicts'],
                'resources': [
                    {'name': 'Git Official Book (Pro Git)', 'url': 'https://git-scm.com/book', 'free': True},
                    {'name': 'Learn Git Branching', 'url': 'https://learngitbranching.js.org/', 'free': True},
                    {'name': 'GitHub Skills', 'url': 'https://skills.github.com/', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Create 3 public GitHub repos', 'Practice branching workflow', 'Submit a pull request'],
                'platforms': ['GitHub', 'GitLab', 'Bitbucket'],
            },
            'build': {
                'projects': ['Personal portfolio on GitHub Pages', 'Open source contribution'],
            },
            'apply': {
                'actions': ['Maintain active GitHub profile', 'Contribute to open source', 'Link GitHub on resume'],
            },
        },
    },
    'Data Structures': {
        'priority': 'high',
        'duration': '6-8 weeks',
        'stages': {
            'learn': {
                'topics': ['Arrays & Strings', 'Linked Lists', 'Stacks & Queues', 'Trees & Graphs', 'Hashing & Heaps', 'Sorting & Searching'],
                'resources': [
                    {'name': 'CS50 - Harvard', 'url': 'https://cs50.harvard.edu/', 'free': True},
                    {'name': 'NeetCode DSA', 'url': 'https://neetcode.io/', 'free': True},
                    {'name': 'GeeksForGeeks', 'url': 'https://www.geeksforgeeks.org/data-structures/', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Solve 50+ LeetCode problems', 'Daily challenge streak', 'Mock interview sessions'],
                'platforms': ['LeetCode', 'HackerRank', 'NeetCode', 'Codeforces'],
            },
            'build': {
                'projects': ['Implement linked list from scratch', 'Build a LRU Cache', 'Graph traversal visualizer'],
            },
            'apply': {
                'actions': ['Apply to FAANG internships', 'Practice system design', 'Mock interviews on Pramp'],
            },
        },
    },
    'Pandas': {
        'priority': 'medium',
        'duration': '2-3 weeks',
        'stages': {
            'learn': {
                'topics': ['DataFrames & Series', 'Data loading (CSV, JSON, Excel)', 'Filtering & groupby', 'Merge & join', 'Data cleaning'],
                'resources': [
                    {'name': 'Pandas Official Documentation', 'url': 'https://pandas.pydata.org/docs/', 'free': True},
                    {'name': 'Kaggle Pandas Course', 'url': 'https://www.kaggle.com/learn/pandas', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Analyze COVID-19 dataset', 'Clean messy CSV data', 'EDA on Titanic dataset'],
                'platforms': ['Kaggle', 'Google Colab', 'Jupyter Notebook'],
            },
            'build': {
                'projects': ['Sales data analysis report', 'Financial data EDA notebook'],
            },
            'apply': {
                'actions': ['Add Pandas to resume', 'Share notebooks on Kaggle', 'Apply to data analyst roles'],
            },
        },
    },
    'TensorFlow': {
        'priority': 'medium',
        'duration': '4-6 weeks',
        'stages': {
            'learn': {
                'topics': ['Tensors & computations', 'Keras API', 'Building neural networks', 'Training & evaluation', 'Model saving & deployment'],
                'resources': [
                    {'name': 'TensorFlow Official Tutorials', 'url': 'https://www.tensorflow.org/tutorials', 'free': True},
                    {'name': 'DeepLearning.AI TF Developer', 'url': 'https://www.coursera.org/specializations/tensorflow-in-practice', 'free': False},
                ],
            },
            'practice': {
                'exercises': ['MNIST digit recognition', 'Image classification with CNNs', 'Text sentiment analysis'],
                'platforms': ['Google Colab', 'Kaggle', 'TensorFlow Playground'],
            },
            'build': {
                'projects': ['Image classifier app', 'Chatbot with TF/Keras'],
            },
            'apply': {
                'actions': ['Get TensorFlow Developer Certificate', 'Deploy model as API', 'Write Kaggle notebook'],
            },
        },
    },
    'Node.js': {
        'priority': 'high',
        'duration': '3-4 weeks',
        'stages': {
            'learn': {
                'topics': ['Event loop & async I/O', 'Express.js framework', 'REST API design', 'Middleware', 'Database integration'],
                'resources': [
                    {'name': 'Node.js Official Docs', 'url': 'https://nodejs.org/docs/', 'free': True},
                    {'name': 'Full Stack Open (NodeJS)', 'url': 'https://fullstackopen.com/en/part3', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Build a REST API', 'Implement authentication', 'Connect to MongoDB'],
                'platforms': ['Replit', 'GitHub', 'Railway'],
            },
            'build': {
                'projects': ['REST API with Express + MongoDB', 'Real-time chat with Socket.io'],
            },
            'apply': {
                'actions': ['Deploy API to Railway/Render', 'Add to portfolio', 'Apply to backend roles'],
            },
        },
    },
    'Selenium': {
        'priority': 'medium',
        'duration': '2-3 weeks',
        'stages': {
            'learn': {
                'topics': ['WebDriver setup', 'Locating elements (XPath, CSS)', 'Interactions: click, type, submit', 'Wait strategies', 'Page Object Model'],
                'resources': [
                    {'name': 'Selenium Docs', 'url': 'https://www.selenium.dev/documentation/', 'free': True},
                    {'name': 'Selenium with Python (RTFD)', 'url': 'https://selenium-python.readthedocs.io/', 'free': True},
                ],
            },
            'practice': {
                'exercises': ['Automate Google search', 'Login form automation', 'Scrape dynamic content'],
                'platforms': ['Sauce Labs Free Tier', 'Local Chrome WebDriver'],
            },
            'build': {
                'projects': ['Automated test suite for a web app', 'Web scraper with Selenium'],
            },
            'apply': {
                'actions': ['Add to QA portfolio', 'Get ISTQB Foundation', 'Apply to SDET roles'],
            },
        },
    },
}

DEFAULT_SKILL_TEMPLATE = {
    'priority': 'medium',
    'duration': '2-4 weeks',
    'stages': {
        'learn': {
            'topics': ['Core fundamentals', 'Best practices', 'Common use cases', 'Hands-on tutorials'],
            'resources': [
                {'name': 'Official Documentation', 'url': 'https://google.com', 'free': True},
                {'name': 'YouTube Tutorials', 'url': 'https://youtube.com', 'free': True},
                {'name': 'Coursera / Udemy Courses', 'url': 'https://coursera.org', 'free': False},
            ],
        },
        'practice': {
            'exercises': ['Complete official tutorials', 'Build small exercises', 'Solve practice problems'],
            'platforms': ['GitHub', 'Replit', 'CodeSandbox'],
        },
        'build': {
            'projects': ['Mini project applying the skill', 'Real-world application'],
        },
        'apply': {
            'actions': ['Add to skills section', 'Include in projects', 'Mention in interviews'],
        },
    },
}


def generate_roadmap(missing_skills: List[str], career_role: str = '') -> Dict[str, Any]:
    """
    Generate a personalized learning roadmap for missing skills.
    """
    roadmap_items = []

    # Sort by priority
    high_priority = []
    med_priority = []
    low_priority = []

    for skill in missing_skills:
        skill_data = get_skill_data(skill)
        priority = skill_data.get('priority', 'medium')
        if priority == 'high':
            high_priority.append((skill, skill_data))
        elif priority == 'medium':
            med_priority.append((skill, skill_data))
        else:
            low_priority.append((skill, skill_data))

    ordered = high_priority + med_priority + low_priority

    for skill, data in ordered[:12]:  # Cap at 12 skills
        item = {
            'skill': skill,
            'priority': data.get('priority', 'medium'),
            'duration': data.get('duration', '2-4 weeks'),
            'stages': data.get('stages', DEFAULT_SKILL_TEMPLATE['stages']),
            'completed': False,
        }
        roadmap_items.append(item)

    # Create stage summary
    stage_summary = {
        'learn': len(roadmap_items),
        'practice': len(roadmap_items),
        'build': max(len(roadmap_items) - 2, 1),
        'apply': max(len(roadmap_items) - 4, 1),
    }

    # Estimated total duration
    total_weeks = estimate_total_duration(roadmap_items)

    return {
        'career_role': career_role,
        'roadmap_items': roadmap_items,
        'total_skills': len(roadmap_items),
        'total_weeks_estimate': total_weeks,
        'stage_summary': stage_summary,
        'phases': [
            {'phase': 'Learn', 'icon': '📚', 'description': 'Study concepts and theory', 'color': '#6366f1'},
            {'phase': 'Practice', 'icon': '💪', 'description': 'Solve exercises and challenges', 'color': '#8b5cf6'},
            {'phase': 'Build', 'icon': '🛠️', 'description': 'Create projects and portfolios', 'color': '#a78bfa'},
            {'phase': 'Apply', 'icon': '🚀', 'description': 'Apply to real opportunities', 'color': '#c4b5fd'},
        ],
    }


def get_skill_data(skill: str) -> dict:
    """Get roadmap data for a skill, falling back to template."""
    # Try exact match
    if skill in SKILL_ROADMAP_DB:
        return SKILL_ROADMAP_DB[skill]

    # Try case-insensitive match
    skill_lower = skill.lower()
    for key, val in SKILL_ROADMAP_DB.items():
        if key.lower() == skill_lower or skill_lower in key.lower():
            return val

    # Return custom template with skill name
    template = dict(DEFAULT_SKILL_TEMPLATE)
    return template


def estimate_total_duration(items: list) -> int:
    """Estimate total learning duration in weeks."""
    total = 0
    for item in items:
        dur = item.get('duration', '2-4 weeks')
        nums = [int(x) for x in dur.split() if x.isdigit()]
        if nums:
            total += sum(nums) // len(nums)
    return total
