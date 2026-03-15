# Finsurance

## Inspiration

Understanding healthcare bills and insurance policies can be extremely confusing. Medical bills often contain complex charges, while insurance contracts are filled with dense legal language that most people do not have the time or expertise to analyze. As a result, many people end up paying more than necessary or missing benefits that they already pay for in their policies.

We wanted to build a tool that bridges the gap between what people are charged and what their insurance actually covers. Our goal was to make insurance transparency simple and accessible.

## What it does

Finsurance acts as a personal insurance and financial assistant. Users upload their insurance contract and recent medical bills, and the system analyzes both documents to determine whether the user is fully utilizing their insurance benefits.

The platform identifies mismatches between billed charges and covered services. It highlights potential missed coverage and explains how effectively the user's current insurance plan supports their medical expenses.

Beyond analyzing current bills, Finsurance also compares the user's policy with other insurance plans in our dataset. The system provides recommendations showing whether a different policy could provide better coverage or lower costs.

## How we built it

We built an AI powered pipeline that processes and analyzes complex documents.
- First, Large Language Models scan uploaded contracts and medical bills and convert them into structured, searchable data.

- Next, an AI reasoning layer compares the medical charges with the rules and benefits defined in the insurance policy. This allows the system to evaluate whether each charge should be covered.

- Finally, the platform compares the user's plan with other policies in our dataset and generates personalized recommendations for improving coverage or reducing costs.

## Challenges we ran into

Our biggest challenge was coordination and integration across the team. Early in development, the project scope was not fully defined, which led to different assumptions about how the system should function.

Later in the project we also faced technical challenges when integrating the AI backend with the frontend interface. The pipeline initially failed to synchronize correctly, which delayed deployment and required additional debugging and testing.

## Accomplishments that we are proud of

We successfully created a working system that can analyze real world insurance documents and medical bills, then convert that information into clear recommendations for users.

Transforming complex financial and healthcare data into understandable insights was a major milestone for our team.

## What we learned

We learned how to build AI systems that retrieve and analyze information from documents such as PDFs and CSV files using Retrieval Augmented Generation (RAG). We also discovered the flexibility of prompt driven AI workflows compared to traditional rule based systems.

Equally important, we learned how critical early project planning and clear communication are when working in a team.

## What's next for Finsurance
### Custom AI Models
Currently, our system relies on external AI APIs. Our next goal is to train a specialized AI model focused specifically on insurance analysis. This will reduce operating costs and improve performance.

### Expanded Datasets
We plan to collect a larger dataset of insurance policies and billing structures. A broader dataset will allow our recommendation system to provide more accurate and diverse suggestions.

### User Experience and Security
We plan to build a full authentication system with login and signup functionality so users can securely store their history. Because the platform handles sensitive financial and personal data, we will also implement strong encryption and database security protections.