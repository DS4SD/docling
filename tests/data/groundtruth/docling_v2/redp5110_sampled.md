<!-- image -->

## Row and Column Access Control

<!-- image -->

<!-- image -->

## Contents

Solution Brief

<!-- image -->

## Highlights

- /g115/g3
- /g115/g3
- /g115/g3
- /g115/g3

<!-- image -->

Power Services

## DB2 for i

Expert help to achieve your business requirements

## We build confident, satisfied clients

No one else has the vast consulting experiences, skills sharing and

Because no one else is IBM.

With combined experiences and direct access to development groups,

## Who we are, some of what we do

Global CoE engagements cover topics including:

- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;
- rglyph&lt;c=1,font=/NKDKKL+JansonTextLTStd-Roman&gt;

## Preface

This IBMfi Redpaper™ publication provides information about the IBM i 7.2 feature of IBM

This paper is intended for database engineers, data-centric application developers, and

This paper was produced by the IBM DB2 for i Center of Excellence team in partnership with

<!-- image -->

Jim Bainbridge

<!-- image -->

Hernando Bedoya

## Authors

<!-- image -->

1

## Securing and protecting IBM DB2

Recent news headlines are filled with reports of data breaches and cyber-attacks impacting

Businesses must make a serious effort to secure their data and recognize that securing

This chapter describes how you can secure and protect data in DB2 for i. The following topics

- /SM590000
- /SM590000
- /SM590000

## 1.1  Security fundamentals

Before reviewing database security techniques, there are two fundamental steps in securing

- /SM590000
- The monitoring and assessment of adherence to the security policy determines whether

A security policy is what defines whether the system and its settings are secure (or not).

- /SM590000

With your eyes now open to the importance of securing information assets, the rest of this

## 1.2  Current state of IBM i security

Because of the inherently secure nature of IBM i, many clients rely on the default system

Even more disturbing is that many IBM i clients remain in this state, despite the news

Traditionally, IBM i applications have employed menu-based security to counteract this default

Many businesses are trying to limit data access to a need-to-know basis. This security goal

## 1.3.1  Existing row and column control

Some IBM i clients have tried augmenting the all-or-nothing object-level security with SQL

Using SQL views to limit access to a subset of the data in a table also has its own set of

Even if you are willing to live with these performance and management issues, a user with

Figure 1-2   Existing row and column controls

<!-- image -->

## 2.1.6  Change Function Usage CL command

The following CL commands can be used to work with, display, or change function usage IDs:

- /SM590000
- /SM590000
- /SM590000

For example, the following

CHGFCNUSG FCNID(QIBM\_DB\_SECADM) USER(HBEDOYA) USAGE(*ALLOWED)

## 2.1.7  Verifying function usage IDs for RCAC with the FUNCTION\_USAGE view

The FUNCTION\_USAGE view contains function usage configuration details. Table 2-1

Table 2-1   FUNCTION\_USAGE view

To discover who has authorization to define and manage RCAC, you can use the query that is

SELECT     function\_id,

user\_type

FROM       function\_usage

WHERE      function\_id='QIBM\_DB\_SECADM'

ORDER BY   user\_name;

## 2.2  Separation of duties

Separation of duties helps businesses comply with industry regulations or organizational

For example, assume that a business has assigned the duty to manage security on IBM i to

In IBM i 7.2, the QIBM\_DB\_SECADM function usage grants authorities, revokes authorities,

QIBM\_DB\_SECADM function usage can be granted only by a user with *SECADM special

QIBM\_DB\_SECADM also is responsible for administering RCAC, which restricts which rows

A preferred practice is that the RCAC administrator has the QIBM\_DB\_SECADM function

Table 2-2 shows a comparison of the different function usage IDs and *JOBCTL authority to

Table 2-2    Comparison of the different function usage IDs and *JOBCTL authority

Figure 3-1   CREATE PERMISSION SQL statement

<!-- image -->

## Column mask

A column mask is a database object that manifests a column value access control rule for a

Table 3-1   Special registers and their corresponding values

Figure 3-5 shows the difference in the special register values when an adopted authority is

- /SM590000
- /SM590000
- /SM590000
- /SM590000
- /SM590000

Figure 3-5   Special registers and adopted authority

<!-- image -->

## 3.2.2  Built-in global variables

Built-in global variables are provided with the database manager and are used in SQL

IBM DB2 for i supports nine different built-in global variables that are read only and

Table 3-2 lists the nine built-in global variables.

Table 3-2   Built-in global variables

## 3.3  VERIFY\_GROUP\_FOR\_USER function

The VERIFY\_GROUP\_FOR\_USER function was added in IBM i 7.2. Although it is primarily

If a special register value is in the list of user profiles or it is a member of a group profile

Here is an example of using the VERIFY\_GROUP\_FOR\_USER function:

- 1.
- 2.
- 3.

```
VERIFY_GROUP_FOR_USER (CURRENT_USER, 'MGR')
```

```
VERIFY_GROUP_FOR_USER (CURRENT_USER, 'JANE', 'MGR', 'STEVE')
```

RETURN

CASE

```
WHEN VERIFY_GROUP_FOR_USER ( SESSION_USER , 'HR', 'EMP' ) = 1
```

- 2.
- -
- -
- -
- -
- To implement this column mask, run the SQL statement that is shown in Example 3-9.

```
CREATE MASK   HR_SCHEMA.MASK_TAX_ID_ON_EMPLOYEES
```

- 3.

Figure 3-10   Column masks shown in System i Navigator

<!-- image -->

## 3.6.6  Activating RCAC

Now that you have created the row permission and the two column masks, RCAC must be

- 1.

## Example 3-10   Activating RCAC on the EMPLOYEES table

- /*   Active Row Access Control (permissions)  */
- /*   Active Column Access Control (masks)     */

ACTIVATE COLUMN ACCESS CONTROL;

- 2.

Figure 3-11   Selecting the EMPLOYEES table from System i Navigator

<!-- image -->

- 2.
- 3.

Figure 4-68   Visual Explain with RCAC enabled

<!-- image -->

Figure 4-69   Index advice with no RCAC

<!-- image -->

```
THEN C . CUSTOMER_TAX_ID
```

```
CREATE MASK BANK_SCHEMA.MASK_SECURITY_QUESTION_ANSWER_ON_CUSTOMERS ON BANK_SCHEMA.CUSTOMERS AS C
```

## Row and Column Access Control

Implement roles and

This IBM Redpaper publication provides information about the IBM i 7.2

Leverage row

Protect columns by

This paper is intended for database engineers, data-centric application

<!-- image -->

<!-- image -->

INTERNATIONAL

BUILDING TECHNICAL

IBM Redbooks are developed

For more information: