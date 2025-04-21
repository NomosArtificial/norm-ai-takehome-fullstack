This repository contains a client and server codebase. 

## Server Repository:

This codebase contains a list of laws (`docs/laws.pdf`) taken from the fictional series “Game of Thrones” (randomly pulled from a wiki fandom site... unfortunately knowledge of the series does not provide an edge on this assignment). Your task is to implement a new service (described in take home exercise document) and provide access to that service via a FastAPI endpoint running in a docker container. Please replace this readme with the steps required to run your app.

### How to run

You can interact with the backend server through a locally deployed fastapi server using Docker. 

Run the following commands from the root of this directory to build the Docker compatible image and launch a Docker container:

```
docker build -t norm-fullstack .
docker run -p 8000:80 -e OPENAI_API_KEY=$OPENAI_API_KEY norm-fullstack
```

You can now navigate to http://localhost:8000/docs to see the openapi schema for the server as well as interact with the endpoints. You'll see two endpoints in the documentation:

- `GET /v1/live`: For health checks
- `POST /v1/query`: Primary business logic endpoint for answering queries

You can try interacting with these endpoints through the docs page mentioned abvoe or with your favorite tool for hitting restful services (e.g...)

```
# Health check
curl http://localhost:8000/v1/live

# Query endpoint
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what happens if I steal from the Sept?"}'
```

### How to evaluate

Being able to test that the application is working with one-off examples is important, but it wont give us a complete sense of the performance of our RAG app. To do this, we need to build an evaluation dataset and generate metrics that we can compare different versions of our app against.

In `eval_data/dataset.jsonl` we've created a small dataset of input queries and expected outputs. Each input can have several `expected_output` objects, with each object containing the following fields:
- `field`: part of the response to assess (e.g. response, citation-source)
- `type`: what kind of assessment to perform (note: right now we only have built-in types but in the future this could point to a custom evaluator implementation)
- `values`: a list of reference or expected outputs to compare the predicted output against

Running the evaluation script is currently fairly rudimentary. As you make changes to your DocumentService or QdrantService in utils, the changes will be imported into the main function of `evaluate.py` and thus leveraged in a new evaluation run by calling `python app/evaluate.py`. In the future, we will want to better specify the inputs to the evaluate script as a declarative configuration file.


### Design choices

There are two primary design choices for this RAG application: 1) how to index the laws, and 2) how to retrieve the laws based on the query and inject into the prompt. 

#### How to index
There are various methods for chunking the source laws pdf document into individual documents in our index. After viewing the laws, I made the following two observations that influenced my indexing design choice: 
1. Law "sections" _can_ be marked by a number-indexed prefix (e.g. 4.1, 3.1.1), but are _always_ in bold
2. The sub-sections within a law section often have wording that is semantically dependent on each other (e.g. 4.2.1 Any knight accused of wrongdoing is allowed by law to demand a trial by combat. The right to a trial by combat also extends to nobles who are not knighted. 4.2.2. The accused and accusers are allowed to have champions fight in their place.)

Because of these observations, I decided to combine all sub-sections into a single document under the boldened top level section. This approach would certainly not scale if a particular section had many sub-sections, in which case other strategies would be considered and then evaluated.

Alternate strategy if given more time: Concatenate all texts in a tree path together into a single document (e.g. texts 4.1, 4.1.1, 4.1.1.2 would be concatenated together into a document and tagged with the metadata section associated with the root node)

#### How to retrieve:
For retrieving we relied on LlamaIndex's CitationQueryEngine for which more information can be found [here](https://docs.llamaindex.ai/en/stable/examples/query_engine/citation_query_engine/)

## Client Repository 

In the `frontend` folder you'll find a light NextJS app with it's own README including instructions to run. Your task here is to build a minimal client experience that utilizes the service build in part 1.
