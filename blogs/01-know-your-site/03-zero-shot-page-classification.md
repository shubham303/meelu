# Classifying Every Page Without Training Data

**Topic suggestion:** Classifying Every Page Without Training Data

**Summary:** Use an LLM or a zero-shot classifier to answer fixed choice questions per page: page type, money page or blog, intent. Cover why multiple-choice questions beat free text, caching by content hash, and when to switch to a trained classifier.

**Approach:** Both

**Grounded in Meelu:** Page classification runs on the server after each crawl through the json_data_extractor facade. See research_notes/…/zero_shot_classifiers.md.
