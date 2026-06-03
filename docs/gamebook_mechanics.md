# Research Note: Gamebook Mechanics & Graph Modeling Strategy

## 1. Exhaustive List of Lone Wolf Game Mechanics

The *Lone Wolf* series relies on a complex set of rules. Below is a comprehensive list of these mechanics:

* **Combat System:** Relies on Combat Skill (CS) and Endurance Points (EP). The combat outcome is determined by the Combat Ratio (Player CS minus Enemy CS) crossed with a Random Number Table (RNT) roll, resulting in simultaneous EP losses per round.
* **Combat Evasion:** The ability to prematurely abort a combat encounter after a certain number of rounds (taking partial damage) to take an alternative narrative path.
* **Endurance Management (Health):** Fluctuates via combat damage, static environmental damage and healing (potions, resting, specific Kai Disciplines like *Healing*).
* **Random Number Table (RNT):** Used for stochastic events and combat resolution.
* **Skill Gates (Kai Disciplines):** Branches of the story that are only accessible if the player chose specific skills at the beginning of the book.
* **Quest Item Dependencies (Keys & Locks):** Delayed dependencies where visiting Node A grants a specific item that is strictly required later at Node B to unlock a specific path to Node C.
* **Inventory & Backpack Management:** A strict limit on items carried (max 8 backpack items, specific slots for weapons and special items).
* **Currency (Gold Crowns):** Accumulation and spending of money to pay for transport, bribes, or items.
* **Survival Mechanics (Meals):** Specific nodes mandate eating a meal. Failure to do so results in an automatic loss of EP (unless the player has the *Hunting* discipline).
* **Equipment Modifiers:** Special items that alter probabilities or stats (e.g., weapons granting +2 CS, or the *Sommerswerd* dealing double damage to undead).
* **Puzzles & Hidden Links:** Textual riddles where the answer is a paragraph number, requiring human comprehension rather than a mechanical link.

## 2. Selected Mechanics for Graph Modeling

To ensure the framework remains computationally viable, easily extractable from raw HTML, and highly **generalizable** to other gamebook franchises, we must select some mechanics to model.

We focus on modelling the following, by decreasing order of importance:

### Topology & Absorbing States (The Base Flow)
* **What it is:** The directed links between paragraphs, including explicit choices, forced transitions, and ending nodes.
* **How to model:** Nodes are paragraphs; directed edges are choices. Endings (Death, Failure, Victory) are modeled as strictly absorbing states (out-degree = 0).

### Probabilistic Branching (Stochastic Edges)
* **What it is:** Random events where a choice does not guarantee a specific destination (RNT events).
* **How to model:** Assigned as weighted probabilities on the edges. 

### Skill Gates as Stochastic Averages
* **What it is:** Paths restricted by Kai Disciplines.
* **How to model:** Instead of fixing a static character build, we model the **statistical average player**. If a player selects 5 out of 10 available disciplines, the probability of possessing any specific discipline is $P = 0.5$. Therefore, a node saying "If you have Sixth Sense, go to X; if not, go to Y" is modeled as a probabilistic split.

### Endurance Dynamics (Health State Expansion & Combat)
* **What it is:** Health management, combat attrition, and combat evasion.
* **How to model:** We use **State Space Expansion**. A node becomes a tuple $(Node\_ID, EP)$. Reaching $EP \le 0$ routes to the global `Death` state. Combat is compressed into a probabilistic transition block, projecting downward edges based on expected EP loss. **Combat Evasion** is modeled as an alternative exit edge from this transition block, splitting the network flow away from the fight-to-the-death scenario, usually coupled with a minor static EP penalty.