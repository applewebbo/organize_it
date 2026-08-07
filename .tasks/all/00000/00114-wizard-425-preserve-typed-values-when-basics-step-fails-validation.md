---
id: '0000000114'
slug: wizard-425-preserve-typed-values-when-basics-step-fails-validation
title: 'Wizard #425: preserve typed values when Basics step fails validation'
labels: []
created: '2026-08-07T08:34:24.200+02:00'
updated: '2026-08-07T08:34:31.899+02:00'
---

## Task Comments

| Commented At | Comment |
| --- | --- |
| 2026-08-07T08:34:31.863+02:00 | Root cause: the stages JSON was injected raw into the inline <script> via {{ form.stages.value }}, so Django's autoescape turned quotes into &quot; and the script threw a SyntaxError. wizardStages() was then undefined, Alpine evaluated x-data to an empty scope and x-model wrote undefined into the date inputs, wiping them. Fix: expose WizardBasicsForm.stages_initial (parsed list) and hydrate via json_script; escapejs on the date seeds. |
| 2026-08-07T08:34:31.899+02:00 | Status changed from ready to complete |
