Aiming to train and evaluate our models in a broader spectrum of table data we have synthesized four types of datasets. Each one contains tables with different appear-

## 1.2. Synthetic datasets the bounding boxes for tables recognized inside PDF docu-

Figure / illustrates the distribution of the tables across different dimensions per dataset.

## tables require the generation of bounding boxes.

## ing FinlabNet, 68% of the simple and 98% of the complex

48% of the simple and 69% of the complex tables. Regard-

## ing FinlabNet, 68% of the simple and 98% of the complex

missing bounding box out of its neighbors. As a first step. we use the annotation data to generate the most fine-grained erid that covers the table structure. In case of strict HIML tables, all grid squares are associated with some table cell and in the presence of table spans a cell extends across multiple grid squares. When enough bounding boxes are known for a rectangular table, it 1s possible to compute the geometrical border lines between the grid rows and columns. Eventually this information 1s used to generate the missing bounding boxes. Additionally, the existence of unused grid Squares indicates that the table rows have unequal number of columns and the overall structure 1s non-strict. [he generation of missing bounding boxes for non-strict HI ML tables 1s ambiguous and therefore quite challenging. lhus, we have decided to simply discard those tables. In case of Pub labNet we have computed missing bounding boxes for

1.1. Data preparation As a first step of our data preparation process, we have calculated statistics over the datasets across the following dimensions: (1) table size measured 1n the number of rows and columns, (2) complexity of the table, (3) strictness of the provided HTML structure and (4) completeness (i.e. no omitted bounding boxes). A table is considered to be simple if it does not contain row spans or column spans. Additionally, a table has a strict HI ML structure 1f every row has the same number of columns after taking into account any row or column spans. [Therefore a strict HI ML structure looks always rectangular. However, HI ML 1s a lenient encoding format, 1.e. tables with rows of different sizes might still be regarded as correct due to implicit display rules. [hese implicit rules leave room for ambiguity, which we want to avoid. As such, we prefer to have 'strict' tables, 1.e. tables where every row has exactly the same length. We have developed a technique that tries to derive a

1. Details on the datasets

ments, this 1s not enough when a full reconstruction of the original table 1s required. [his happens mainly due the following reasons

## Although lableFormer can predict the table structure and

ments

utilized to optimize the runtime overhead of the rendering DIOCESS. 2. Prediction post-processing for PDF docu-

finally rendered by a web browser engine to generate the bounding boxes for each table cell. A batching technique 1s

can be combined with purely random text to produce the synthetic content. 4. Apply styling templates: Depending on the domain of the synthetic dataset, a set of styling templates 1s first manually selected. Ihen, a style is randomly selected to format the appearance of the synthesized table. 5. Render the complete tables: The synthetic table 1s

tentially spans over multiple rows and a table body that may contain a combination of row spans and column spans. However, spans are not allowed to cross the header - body boundary. Ihe table structure 1s described by the parameters: Total number of table rows and columns. number of header rows, type of spans (header only spans, row only spans, column only spans, both row and column spans), maximum span size and the ratio of the table area covered by spans. Generate content: Based on the dataset theme. a set of suitable content templates 1s chosen first. Then, this content

frequently used terms out of non-synthetic datasets (e.g. Pub labNet, Fin LabNet, etc.). 2. Generate table structures: [he structure of each synthetic dataset assumes a horizontal table header which po-

templates have been manually designed and organized into groups of scope specific appearances (e.g. financial data. marketing data, etc.) Additionally, we have prepared curated collections of content templates by extracting the most

up to 600K synthetic examples. All datasets are divided into Train, lest and Val splits (8O%, 10%, 10%). The process of generating a synthetic dataset can be decomposed into the following steps: |. Prepare styling and content templates: The styling

Every synthetic dataset contains 150k examples, summing

## ances in regard to their size, structure, style and content.

TableFormer: Table Structure Understanding with Transformers Supplementary Material