# IA 2.0 - Docs for humans, agents, me and you.

We need to review the IA skill, and evolve it into something that works for both human and AI readers, following Diataxis principles. See [Onafria documentation one pager](docs/onafriq_documentation_playbook_one_pager.md) for reference.

# Audience

When updating the docs for a project, the audience is:

1. You, the agent working on the project. Your memory is limited, so the docs help you remember how things work and what decisions were made. Keep in mind how you process information and write docs for a future version of yourself.
2. Other agents who are at least as capable as you. So in a way, they are similar to your future self. Write docs that are clear and unambiguous for other agents to follow.
3. Engineers who may work on the project in the future. They may not have the same capabilities as you, so write docs that are easy to understand and follow for humans with varying levels of technical expertise.
4. Users who may need to understand how to use the project. Do not neglect user documentation until the very end. When writing or updating docs, also think about how the end user documentation should look.

Importantly, it should be clear whether a piece of documentation is for Agents, Engineers, or Users, or a mixture of these audiences. Especially when instructions are given, who are they for?

Use "For: <audience-types>" tags at the start of documents and at the start of sections or documents when the intended audience is changing.

# User journey

For this skill, the user journey is as follows:

1. For agents, it's either starting a new project or sub-task within a project, or returning to continue an existing project or task.
2. For engineers, it's similarly, either starting a new project or task, or returning to continue an existing one.
3. For users, it's typically starting to use the project or feature for the first time.

# Diataxis types

Use a combination of the user journey and audience to determine the appropriate diataxis types and therefore the documents needed.

For agents starting a new project or task, they will need:
- Tutorials to get started quickly.
- How-to guides for specific tasks.
- Reference documentation for APIs, tools, and libraries used.
- Explanation documents for understanding concepts and decisions. (e.g., architecture decisions, design patterns)
- Explanations on how to build/or mutate the system (less how to use it, more how to make it do new things).

For agents returning to continue a project or task, they will need:
- Continuity guides and hand-off documents to tell them what has been done so far, and what remains to be done.
- How-to guides for specific tasks.
- Reference documentation for APIs, tools, and libraries used.
- Explanation documents for understanding concepts and decisions. (e.g., architecture decisions, design patterns)
- Explanations on how to build/or mutate the system (less how to use it, more how to make it do new things).

Instructions for agents should be clearly marked as such, so they understand that they are being asked to perform a task. Or that they must read a specific document before continuing. Carefully constructed content is key for agents to follow instructions correctly. The wrong order or ambiguous instructions can lead to mistakes.

Agents fixed context windows mean concise and well-structured documentation is essential.

For engineers in both starting and returning scenarios, the needs are similar to agents, but with more verbosity and context, as you may not be able to gauge their capabilities as well as you can for other agents. Therefore, they will need the same docs, but with more detail and explanation. Humans will tend to scan docs more, so use clear headings, summaries, and bullet points to make it easy to find information quickly. They will also tend to skip from section to section, so ensure each section is self-contained and can be understood independently. Finally, they need to know when a piece of information is for an agent, vs, and engineer.

For users, this is where diataxis shines. Users joining the project for the first time will need:
- Tutorials to get started quickly.
- How-to guides for specific tasks.
- Reference documentation for using the project.
- Non-technical explanation documents for understanding concepts and features. (e.g., how a feature works, why certain design decisions were made)   
