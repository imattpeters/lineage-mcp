---
description: Python Working Guidelines
---

# Python - LLM Quick Reference Guide

> **⚠️ CRITICAL FOR LLM AGENTS**: Follow the Zen of Python principles when writing or modifying Python code. Pythonic code is readable, maintainable, and aligns with Python idioms.

## 🎯 Quick Start / Essential Patterns

### Core Principle

Write code that is **explicit, readable, and idiomatic**. Prioritize clarity over cleverness.

### ✅ DO | ❌ DON'T

| DO (Pythonic)                         | DON'T (Unpythonic)               |
| ------------------------------------- | -------------------------------- |
| `for item in items:`                  | `for i in range(len(items)):`    |
| Explicit error handling               | Silently catch all exceptions    |
| Single, obvious way to do something   | Multiple clever approaches       |
| Simple functions over complex nesting | Deeply nested logic              |
| Clear variable names                  | Cryptic abbreviations            |
| Flat structure with namespaces        | Deeply nested inheritance chains |

## 🏛️ The 19 Principles

| #   | Principle                                                 |
| --- | --------------------------------------------------------- |
| 1   | Beautiful is better than ugly.                            |
| 2   | Explicit is better than implicit.                         |
| 3   | Simple is better than complex.                            |
| 4   | Complex is better than complicated.                       |
| 5   | Flat is better than nested.                               |
| 6   | Sparse is better than dense.                              |
| 7   | Readability counts.                                       |
| 8   | Special cases aren't special enough to break the rules.   |
| 9   | Although practicality beats purity.                       |
| 10  | Errors should never pass silently.                        |
| 11  | Unless explicitly silenced.                               |
| 12  | In the face of ambiguity, refuse the temptation to guess. |
| 13  | There should be one-and preferably only one-obvious way.  |
| 14  | Although that way may not be obvious at first.            |
| 15  | Now is better than never.                                 |
| 16  | Although never is often better than right now.            |
| 17  | If implementation is hard to explain, it's a bad idea.    |
| 18  | If implementation is easy to explain, it may be good.     |
| 19  | Namespaces are one honking great idea – let's do more!    |

## 🚨 Best Practices & Common Pitfalls

| Category           | Best Practice                                                   |
| ------------------ | --------------------------------------------------------------- |
| **Readability**    | Code is read more often than written; optimize for readers      |
| **Error Handling** | Never pass errors silently; explicitly handle or log exceptions |
| **Ambiguity**      | When unclear, ask or check existing patterns-don't guess        |
| **Timing**         | Do it now unless deferring is explicitly better                 |
| **Complexity**     | Choose complex solutions over complicated ones; complexity ok   |
| **Namespaces**     | Use modules/packages to organize code; avoid flat structures    |

> **🤖 LLM NOTE**: When writing Python, mentally run through principles 2, 3, 7, and 13. Pythonic code saves everyone time and reduces maintenance burden.