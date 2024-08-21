## mathemastery
#### a project for the HackVortex 4 Hackathon
#### created by Rodion Zuban

![image](https://github.com/user-attachments/assets/ab089d69-767f-4cfd-91e1-9702fd45726c)
<small>The "Learn" screen for a topic in mathemastery. The student can see how far they have progressed, answers to the last problem, their accuracy, and more.</small>

### What is mathemastery? 
Mathemastery is a tool created to aid elementary educators in their job, while making learning more fun and accessible for their students. 

More specifically, it works as follows:
- Teachers can create "classrooms" within the website, allowing them to organize their students in the application and track their progress
- They can then assign an extensive range of topics ranging from kindergarten to 5th grade level to their students.
- Students can then complete problems within these topics, earning a "mastery" once they have progressed sufficiently in the unit.
- Students can always access learning content, regardless of whether the teacher has assigned it or not.

### Why mathemastery?
Mathemastery is a unique and innovative tool based around the concept of allowing teachers to enhance their teaching in only a few clicks. 

Problem sets in mathemastery are pre-generated in an appropriate format for every topic, meaning that the teacher can relax knowing that they do not have to design review problems; mathemastery completes this part for them.

In addition, mathemastery tracks statistics on students such as their accuracy, progress, and time spent on a unit. This allows teachers to better understand what they're working with and overall simply reduce the hassle of their job.

### Repository Layout / Organization
This repository is laid out in standard Flask application format. The backend `app.py` and `helpers.py` files can be located in the main branch, while the HTML content is found in `/templates` and images and CSS can be found in the `/static` folder.
It is important to note that the database and .env files are missing, however this should be expected for security reasons.

### Plans for the Future
The version of mathemastery presented in this repository is its first version, made after a week of development. Some features I would like to add in the future are:
- more topics / types of problems
- a more detailed classroom feature
- further gamification of learning to make new information fun and enjoyable for students.

