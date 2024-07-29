import logging

from langchain.memory import ChatMessageHistory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

if __name__ == "__main__":
    import sys

    sys.path.append("../..")

from common.log_config import handler, log_level

logger = logging.getLogger("AMG Chat-Based Agent")
logger.setLevel(log_level)
logger.addHandler(handler)
from common.model_loader import model

system_message = (
    "You are a senior Java developer. "
    "When you are asked any questions, your answers should be factual, informative, detailed, and most importantly, without hallucination. "
)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

chain = prompt | model.bind(max_tokens=500, presence_penalty=2.0)

chat_history = ChatMessageHistory()
chain = RunnableWithMessageHistory(
    chain,
    lambda _: chat_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)


def invoke_chain(query):
    response = chain.invoke(
        {"input": query}, {"configurable": {"session_id": "unused"}}
    ).content
    logger.debug(f"Query: {query}")
    logger.info(f"Response: {response}")
    return response


intro = "Hello, I am a fellow Java developer. I want to discuss a commit with you. In each of my messages, I will provide some contextual information about the commit and I want to ask you some questions about it."
invoke_chain(intro)


def generate_cm(**kwargs):
    if "diff" in kwargs:
        diff = kwargs["diff"]
        msg = f"First of all, let me show you the diff of the commit:\n{diff}\n\nWhat do you think about the changes made in this commit? What exactly has been changed? Cite the changes based on the diff only."
        invoke_chain(msg)
    invoke_chain("I don't think so. Are you sure? Review your answer.")


if __name__ == "__main__":
    context = {
        "diff": """diff --git a/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java b/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java
index 15321bd07f..e1ab28d7f0 100644
--- a/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java
+++ b/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java
@@ -99,7 +99,7 @@ public class ReferralLut
         
         for ( int ii = 0; ii < dn.size(); ii++ )
         {
-            farthest.add( dn.getRdn( ii ) );
+            farthest.addNormalized( dn.getRdn( ii ) );
 
             // do not return dn if it is the farthest referral
             if ( isReferral( farthest ) && ( farthest.size() != dn.size() ) )
"""
    }
    generate_cm(**context)
