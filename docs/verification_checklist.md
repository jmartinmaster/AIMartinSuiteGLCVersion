# Project Librarian Verification Checklist

Below is a checklist of the new dashboard features to verify. You can select this file (`docs/verification_checklist.md`) in the Task Board dropdown inside the Project Librarian web UI and check off the boxes as you complete each test.

## 1. Index Browser Tab
- [x] Open the **Index Browser** tab in the web UI.
- [x] Verify that the folder cards list the correct files and can expand/collapse.
- [x] Test the **Search Files/Symbols** filter input and dropdowns (Area, Kind).
- [x] Select a symbol (class or function), verify the **Symbol Details** card updates.
- [x] Click the **Load Source Code** button in the details card and verify that the source code excerpt is displayed directly at the bottom of the Index Browser tab.

## 2. Interactive Task Board
- [x] Navigate to the **Task Board** tab.
- [x] Use the **Select Task List File** dropdown and choose `docs/verification_checklist.md` (this file!).
- [x] Check off a few boxes in this checklist and verify they update in real-time (Todo `[ ]` -> In Progress `[/]` -> Done `[x]`).
- [x] Open the actual `docs/verification_checklist.md` file in your editor to verify that the markdown changes were saved.
- [x] Type a test task in the **Add Task** input and verify it appends to the list.
- [x] Type a new list name (e.g. `test-list.md`) in the **Create New List** input, click Create, and verify it initializes a new checklist file and switches to it.

## 3. Server Shutdown
- [x] Click the red **Terminate Server** button in the dashboard header.
- [x] Verify that the browser displays a confirmation popup.
- [X] Click OK and verify that the status banner changes to **Server Terminated** and all buttons on the page become disabled.
- [X] Verify in your terminal that the uvicorn process has exited cleanly.
- [x] Fix Load Source Code so the code is pulled up like source code excerpt but expanded to show the full source code
