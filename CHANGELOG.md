## v1.16.0 (2026-02-21)
- SWUA-173: Add User-Agent handling functionality
- SWUA-177: Add /quizzes/{module_id}/{quiz_id}/attempts endpoint
- SWUA-174: Add endpoint for updating homeworks
- SWUA-171: Fix refresh token blacklisted error
- SWUA-176: Add endpoint for deleting account


## v1.15.0 (2026-02-19)
- SWUA-146: Add drag&drop functionality for questions instances
- SWUA-152: Add user progress history and display only the last completed step
- SWUA-160: Add endpoint for lessons progress
- SWUA-158: Fix multiple homeworks to add in admin panel
- SWUA-166: Add disable to creating new user submission for homework


## v1.14.0 (2026-02-16)
- SWUA-157: Add API with invite to telegram chat
- SWUA-155: Fix progress score recalculation for hidden modules and lessons
- SWUA-153: Add next/previous lessons in API for /lessons/{id} endpoint
- SWUA-148: Add inactive functional for modules and lessons
- SWUA-147: Fix order functional for modules


## v1.13.0 (2026-02-15)
- SWUA-145: Fix recalculation user score
- SWUA-144: Fix changing order for objects in admin panel
- SWUA-139: Add field for max score in API quizes
- SWUA-140: Add description for audio_url and video_url fields
- SWUA-143: Add filters and additional info about users in list_display
- SWUA 142: Fix missing translations
- SWUA-136: Fix changing language in admin panel


## v1.12.0 (2026-02-13)
- SWUA-131: Fix text question type functionality in admin page
- SWUA-85: Add telegram invites functionality


## v1.11.0 (2026-02-12)
- SWUA-90: Fix to validate iteration on mental health
- SWUA-125: Add current user's lessons and modules functionality


## v1.10.0 (2026-02-09)
- SWUA-89: Add saving files functionality
- SWUA-120: Fix remove score issue


## v1.9.0 (2026-02-08)
- SWUA-75: Fix email letters style
- SWUA-106: Add custom admin API
- SWUA-121: Fix adding quiz for lesson issue


## v1.8.0 (2026-02-08)
- SWUA-118: Fix order issues on models
- SWUA-90: Add Mental Health functionality (API + Admin)


## v1.7.0 (2026-02-04)
- SWUA-99: Add fields for approve requirements validation 
- SWUA-110: Update /api/modules endpoint for return less info about lessons 
- SWUA-70: Add API total score of users to display it in main page
- SWUA-108: Update user's activate flow


## v1.6.0 (2026-02-02)
- SWUA-107: Fixes ENUMS in docs
- SWUA-31: Ddd forgot and reset password functionality
- SWUA-72: Add drag & drop functionality


## v1.5.0 (2026-02-02)
- SWUA-104: Update links between module-lesson-quiz models
- Extra fixes for API and API Docs


## v1.4.0 (2026-02-01)
- SWUA-92: Update score lessons algorithm (just for TEXT, VIDEO and AUDIO content types)
- SWUA-80: Edit personal info
- SWUA-86: Update lessons availability
- SWUA-101: Add scored functionality for modules
- SWUA-102: Add custom messages for right and wrongs user responses
- SWUA-97: Update quiz endpoint (add correct answers for /attempts/answers) + removing and refactoring endpoints
- SWUA-95: Update registration fields
- SWUA-81: Button for resend email with activation user link
- SWUA-79: Remake Celery to threads


## v1.3.0 (2026-01-24)
- SWUA-64: Group flow functionality + validation access
- SWUA-69: Saving user process
- SWUA-73: Add coverage [min - 80%]
- SWUA-54: User verification functional (upgrade)


## v1.2.0 (2026-01-19)
- SWUA-49: Module config functionality
- SWUA-54: Implement user verification
- SWUA-68: Homework API
- SWUA-71: Fix text editor styles


## v1.1.0 (2026-01-13)
- SWUA-60: Quiz API functionality
- SWUA-61: Quiz admin functionality
- SWUA-62: Add loguru package


## v1.0.0 (2026-01-03)
- SWUA-55: /users/me endpoint
- SWUA-59: Install commitzen
- SWUA-53: Initial admin panel with new UI
- SWUA-27: /login + /refresh endpoints
- SWUA-22: /registration endpoint
