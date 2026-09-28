#!/usr/bin/env python3
"""
=============================================================================
STUDENT GRADE MANAGEMENT SYSTEM (CLI)
=============================================================================
A modular, high-reliability command-line application built with standard Python
libraries (csv, os, sys) for recording, calculating, analyzing, and persisting
student academic performance data.

Architecture Overview:
----------------------
1. Configuration & Constants : File paths, field names, and grading thresholds.
2. Core Business Logic       : Grade evaluation and statistical aggregations.
3. Persistence Layer         : Resilient CSV read/write with error recovery.
4. Input Validation Subsystem: Safe, loop-based input parsers.
5. Presentation Layer        : Terminal tables, banners, and summary dashboards.
6. Controller Loop           : Main menu dispatching and exception handling.
=============================================================================
"""

import csv
import os
import sys
from typing import Dict, List, Optional, Tuple, Any

# =============================================================================
# 1. CONFIGURATION & CONSTANTS
# =============================================================================

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DATA_FILE: str = os.path.join(BASE_DIR, "students_data.csv")
FIELDNAMES: List[str] = ["ID", "Name", "Marks", "Grade"]

# Standardized Letter Grading Thresholds: (Minimum Marks, Grade Label)
GRADE_THRESHOLDS: List[Tuple[float, str]] = [
    (90.0, "A+"),
    (80.0, "A"),
    (70.0, "B"),
    (60.0, "C"),
    (50.0, "D"),
    (0.0,  "F")
]


# =============================================================================
# 2. CORE BUSINESS LOGIC & GRADE COMPUTATION
# =============================================================================

def calculate_grade(marks: float) -> str:
    """
    Computes a letter grade according to academic performance tiers.
    
    Grading Scale:
      90.00 <= Marks <= 100.00 -> 'A+'
      80.00 <= Marks <  90.00  -> 'A'
      70.00 <= Marks <  80.00  -> 'B'
      60.00 <= Marks <  70.00  -> 'C'
      50.00 <= Marks <  60.00  -> 'D'
      0.00  <= Marks <  50.00  -> 'F'
    """
    for threshold, grade in GRADE_THRESHOLDS:
        if marks >= threshold:
            return grade
    return "F"


def compute_statistics(students: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates statistical aggregates across the entire student dataset.
    
    Returns:
        dict containing count, average, highest scorer, lowest scorer,
        passing rate, and frequency distribution of letter grades.
    """
    if not students:
        return {}

    total_marks = 0.0
    highest_student = students[0]
    lowest_student = students[0]
    grade_distribution = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

    for student in students:
        marks = float(student["Marks"])
        total_marks += marks

        # Update grade distribution count
        grade = student.get("Grade", calculate_grade(marks))
        if grade in grade_distribution:
            grade_distribution[grade] += 1
        else:
            grade_distribution[grade] = 1

        # Track extremes
        if marks > float(highest_student["Marks"]):
            highest_student = student
        if marks < float(lowest_student["Marks"]):
            lowest_student = student

    count = len(students)
    avg_marks = total_marks / count
    passed_count = sum(count for g, count in grade_distribution.items() if g != "F")
    pass_rate = (passed_count / count) * 100.0

    return {
        "total_count": count,
        "average_marks": avg_marks,
        "average_grade": calculate_grade(avg_marks),
        "highest_student": highest_student,
        "lowest_student": lowest_student,
        "pass_rate": pass_rate,
        "grade_distribution": grade_distribution
    }


# =============================================================================
# 3. PERSISTENCE LAYER & DATA ACCESS
# =============================================================================

def initialize_storage() -> None:
    """
    Ensures that the CSV data store exists and contains proper headers.
    If the file does not exist, an empty initialized file is created.
    """
    if not os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
                writer.writeheader()
        except OSError as e:
            print(f"\n[CRITICAL ERROR] Unable to initialize storage file at '{DATA_FILE}': {e}")


def load_students() -> List[Dict[str, Any]]:
    """
    Reads all student records from the CSV file.
    
    Robustness Features:
      - Ignores corrupted rows with missing or malformed marks.
      - Strips accidental whitespaces.
      - Recomputes missing/inconsistent grades dynamically.
    """
    initialize_storage()
    students: List[Dict[str, Any]] = []

    if not os.path.exists(DATA_FILE):
        return students

    try:
        with open(DATA_FILE, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            # Check for missing headers or empty file
            if reader.fieldnames is None:
                return students

            for line_no, row in enumerate(reader, start=2):
                student_id = (row.get("ID") or "").strip()
                name = (row.get("Name") or "").strip()
                raw_marks = (row.get("Marks") or "").strip()

                if not student_id or not name:
                    continue  # Skip incomplete record entries

                try:
                    marks = float(raw_marks)
                    if not (0.0 <= marks <= 100.0):
                        continue
                except ValueError:
                    # Skip rows with non-numeric marks
                    continue

                grade = calculate_grade(marks)
                students.append({
                    "ID": student_id,
                    "Name": name,
                    "Marks": marks,
                    "Grade": grade
                })
    except Exception as e:
        print(f"\n[WARNING] Error reading '{DATA_FILE}': {e}. System will continue with recoverable data.")
    
    return students


def save_students(students: List[Dict[str, Any]]) -> bool:
    """
    Persists student records to the CSV file safely.
    Writes atomically to maintain data integrity.
    """
    temp_file = DATA_FILE + ".tmp"
    try:
        with open(temp_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()
            for s in students:
                writer.writerow({
                    "ID": s["ID"],
                    "Name": s["Name"],
                    "Marks": f"{float(s['Marks']):.2f}",
                    "Grade": s["Grade"]
                })
        
        # Atomic replacement of old storage file
        if os.path.exists(DATA_FILE):
            os.replace(temp_file, DATA_FILE)
        else:
            os.rename(temp_file, DATA_FILE)
        return True
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        print(f"\n[ERROR] Failed to save student records to disk: {e}")
        return False


# =============================================================================
# 4. INPUT VALIDATION & PROMPT HELPERS
# =============================================================================

def get_non_empty_string(prompt_label: str) -> str:
    """Prompts the user repeatedly until a non-empty string is provided."""
    while True:
        value = input(prompt_label).strip()
        if value:
            return value
        print("  [!] Field cannot be empty or only spaces. Please try again.")


def get_valid_marks(prompt_label: str = "Enter Marks (0 - 100): ") -> float:
    """Prompts until a valid numerical mark within [0.0, 100.0] is entered."""
    while True:
        raw = input(prompt_label).strip()
        if not raw:
            print("  [!] Marks cannot be blank.")
            continue
        try:
            marks = float(raw)
            if 0.0 <= marks <= 100.0:
                return round(marks, 2)
            print("  [!] Out of range: Marks must be between 0.0 and 100.0.")
        except ValueError:
            print("  [!] Invalid number: Please enter a valid decimal or integer value.")


def get_unique_student_id(existing_students: List[Dict[str, Any]]) -> str:
    """Prompts for a unique Student ID, checking against current records."""
    existing_ids = {str(s["ID"]).strip().lower() for s in existing_students}
    while True:
        student_id = get_non_empty_string("Enter Unique Student ID: ")
        if student_id.lower() in existing_ids:
            print(f"  [!] ID '{student_id}' is already assigned to an existing record. Please use a unique ID.")
            continue
        return student_id


# =============================================================================
# 5. PRESENTATION & DASHBOARD VIEWS
# =============================================================================

def print_header(title: str, width: int = 72) -> None:
    """Renders a structured, clean terminal section header."""
    print("\n" + "=" * width)
    print(f" {title.center(width - 2)} ")
    print("=" * width)


def add_student_view() -> None:
    """Controller view for enrolling a new student record."""
    print_header("ADD NEW STUDENT RECORD")
    students = load_students()
    
    student_id = get_unique_student_id(students)
    name = get_non_empty_string("Enter Student Full Name: ")
    marks = get_valid_marks("Enter Final Marks (0 - 100): ")
    grade = calculate_grade(marks)

    new_record = {
        "ID": student_id,
        "Name": name,
        "Marks": marks,
        "Grade": grade
    }
    students.append(new_record)

    if save_students(students):
        print("-" * 72)
        print(" [✓] SUCCESS: Student record successfully committed to database!")
        print(f"     ID     : {student_id}")
        print(f"     Name   : {name}")
        print(f"     Marks  : {marks:.2f} / 100.00")
        print(f"     Grade  : {grade}")
        print("-" * 72)
    else:
        print(" [✗] ERROR: Could not write record to storage file.")


def view_all_students_view() -> None:
    """Displays all records in a formatted ASCII table along with aggregate stats."""
    print_header("STUDENT ACADEMIC REGISTRY & PERFORMANCE SUMMARY")
    students = load_students()

    if not students:
        print("\n  [i] No student records found. Select option [1] to add a student.\n")
        print("=" * 72)
        return

    # Table Header
    print(f"{'No.':<5} | {'Student ID':<14} | {'Student Name':<26} | {'Marks':<10} | {'Grade':<6}")
    print("-" * 72)

    for idx, s in enumerate(students, start=1):
        marks_val = float(s["Marks"])
        name_display = (s["Name"][:23] + "...") if len(s["Name"]) > 26 else s["Name"]
        print(f"{idx:<5} | {s['ID']:<14} | {name_display:<26} | {marks_val:<10.2f} | {s['Grade']:<6}")

    print("=" * 72)

    # Rich Summary Statistics Dashboard
    stats = compute_statistics(students)
    hi = stats["highest_student"]
    lo = stats["lowest_student"]
    dist = stats["grade_distribution"]

    print("                       PERFORMANCE ANALYTICS                      ")
    print("-" * 72)
    print(f" Total Enrolled Students : {stats['total_count']}")
    print(f" Class Average Marks     : {stats['average_marks']:.2f} / 100.00 (Grade: {stats['average_grade']})")
    print(f" Passing Rate            : {stats['pass_rate']:.1f}%")
    print(f" Highest Achiever        : {hi['Name']} (ID: {hi['ID']}) - {float(hi['Marks']):.2f} marks [{hi['Grade']}]")
    print(f" Lowest Achiever         : {lo['Name']} (ID: {lo['ID']}) - {float(lo['Marks']):.2f} marks [{lo['Grade']}]")
    print("-" * 72)
    print(" Grade Distribution Breakdown:")
    dist_str = " | ".join(f"{g}: {count}" for g, count in dist.items())
    print(f"  ->  {dist_str}")
    print("=" * 72)


def search_student_view() -> None:
    """Searches and outputs student record details matching an ID."""
    print_header("SEARCH STUDENT RECORD BY ID")
    search_id = input("Enter Student ID to look up: ").strip()

    if not search_id:
        print(" [!] Search query cannot be blank.")
        return

    students = load_students()
    matches = [s for s in students if str(s["ID"]).strip().lower() == search_id.lower()]

    if matches:
        student = matches[0]
        marks_val = float(student["Marks"])
        print("\n [✓] RECORD MATCH LOCATED:")
        print("-" * 48)
        print(f"  • Student ID     : {student['ID']}")
        print(f"  • Full Name      : {student['Name']}")
        print(f"  • Obtained Marks : {marks_val:.2f} / 100.00")
        print(f"  • Letter Grade   : {student['Grade']}")
        print("-" * 48)
    else:
        print(f"\n [✗] No student record matches the ID '{search_id}'.")


def delete_student_view() -> None:
    """Removes a student record upon explicit user confirmation."""
    print_header("DELETE STUDENT RECORD")
    target_id = input("Enter Student ID to remove: ").strip()

    if not target_id:
        print(" [!] Target ID cannot be empty.")
        return

    students = load_students()
    target_index: Optional[int] = None

    for idx, s in enumerate(students):
        if str(s["ID"]).strip().lower() == target_id.lower():
            target_index = idx
            break

    if target_index is None:
        print(f"\n [✗] Student with ID '{target_id}' does not exist.")
        return

    record = students[target_index]
    print(f"\n Target Record: {record['Name']} (ID: {record['ID']}, Marks: {float(record['Marks']):.2f}, Grade: {record['Grade']})")
    confirm = input(" Are you sure you want to permanently delete this record? [y/N]: ").strip().lower()

    if confirm in ["y", "yes"]:
        del students[target_index]
        if save_students(students):
            print(f"\n [✓] SUCCESS: Record for ID '{target_id}' has been permanently deleted.")
        else:
            print("\n [✗] ERROR: Failed to update database file.")
    else:
        print("\n [-] ACTION CANCELLED: Record was not modified.")


# =============================================================================
# 6. MAIN CONTROLLER & APPLICATION LOOP
# =============================================================================

def render_main_menu() -> None:
    """Prints the primary application navigation dashboard."""
    print("\n" + "=" * 54)
    print("   🎓  STUDENT GRADE MANAGEMENT SYSTEM (CLI)  🎓   ")
    print("=" * 54)
    print("  [1] Enroll / Add New Student")
    print("  [2] View All Students & Performance Analytics")
    print("  [3] Search Student by ID")
    print("  [4] Delete Student Record")
    print("  [5] Exit Application")
    print("=" * 54)


def main() -> None:
    """Main execution loop controlling user interactions."""
    initialize_storage()

    while True:
        try:
            render_main_menu()
            choice = input(" Select an option (1-5): ").strip()

            if choice == "1":
                add_student_view()
            elif choice == "2":
                view_all_students_view()
            elif choice == "3":
                search_student_view()
            elif choice == "4":
                delete_student_view()
            elif choice == "5":
                print("\n" + "=" * 54)
                print("  Thank you for using Student Grade Management System!")
                print("  Session ended cleanly. Goodbye.")
                print("=" * 54 + "\n")
                sys.exit(0)
            else:
                print("\n [!] Invalid selection. Please enter a numerical option between 1 and 5.")
        except KeyboardInterrupt:
            print("\n\n [!] Interrupt received. Exiting safely...")
            sys.exit(0)
        except Exception as err:
            print(f"\n [CRITICAL ERROR] An unexpected exception occurred: {err}")


if __name__ == "__main__":
    main()
