import copy
import logging

import networkx as nx

logger = logging.getLogger("layout_utils")


## -------------------------------
## Geometric helper functions
## The coordinates grow left to right, and bottom to top.
## The bounding box list elements 0 to 3 are x_left, y_bottom, x_right, y_top.


def area(bbox):
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def contains(bbox_i, bbox_j):
    ## Returns True if bbox_i contains bbox_j, else False
    return (
        bbox_i[0] <= bbox_j[0]
        and bbox_i[1] <= bbox_j[1]
        and bbox_i[2] >= bbox_j[2]
        and bbox_i[3] >= bbox_j[3]
    )


def is_intersecting(bbox_i, bbox_j):
    return not (
        bbox_i[2] < bbox_j[0]
        or bbox_i[0] > bbox_j[2]
        or bbox_i[3] < bbox_j[1]
        or bbox_i[1] > bbox_j[3]
    )


def bb_iou(boxA, boxB):
    # determine the (x, y)-coordinates of the intersection rectangle
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    # compute the area of intersection rectangle
    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    # compute the area of both the prediction and ground-truth
    # rectangles
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = interArea / float(boxAArea + boxBArea - interArea)
    # return the intersection over union value
    return iou


def compute_intersection(bbox_i, bbox_j):
    ## Returns the size of the intersection area of the two boxes
    if not is_intersecting(bbox_i, bbox_j):
        return 0
    ## Determine the (x, y)-coordinates of the intersection rectangle:
    xA = max(bbox_i[0], bbox_j[0])
    yA = max(bbox_i[1], bbox_j[1])
    xB = min(bbox_i[2], bbox_j[2])
    yB = min(bbox_i[3], bbox_j[3])
    ## Compute the area of intersection rectangle:
    interArea = (xB - xA) * (yB - yA)
    if interArea < 0:
        logger.debug("Warning: Negative intersection detected!")
        return 0
    return interArea


def surrounding(bbox_i, bbox_j):
    ## Computes minimal box that contains both input boxes
    sbox = []
    sbox.append(min(bbox_i[0], bbox_j[0]))
    sbox.append(min(bbox_i[1], bbox_j[1]))
    sbox.append(max(bbox_i[2], bbox_j[2]))
    sbox.append(max(bbox_i[3], bbox_j[3]))
    return sbox


def surrounding_list(bbox_list):
    ## Computes minimal box that contains all boxes in the input list
    ## The list should be non-empty, but just in case it's not:
    if len(bbox_list) == 0:
        sbox = [0, 0, 0, 0]
    else:
        sbox = []
        sbox.append(min([bbox[0] for bbox in bbox_list]))
        sbox.append(min([bbox[1] for bbox in bbox_list]))
        sbox.append(max([bbox[2] for bbox in bbox_list]))
        sbox.append(max([bbox[3] for bbox in bbox_list]))
    return sbox


def vertical_overlap(bboxA, bboxB):
    ## bbox[1] is the lower bound, bbox[3] the upper bound (larger number)
    if bboxB[3] < bboxA[1]:  ## B below A
        return False
    elif bboxA[3] < bboxB[1]:  ## A below B
        return False
    else:
        return True


def vertical_overlap_fraction(bboxA, bboxB):
    ## Returns the vertical overlap as fraction of the lower bbox height.
    ## bbox[1] is the lower bound, bbox[3] the upper bound (larger number)
    ## Height 0 is permitted in the input.
    heightA = bboxA[3] - bboxA[1]
    heightB = bboxB[3] - bboxB[1]
    min_height = min(heightA, heightB)
    if bboxA[3] >= bboxB[3]:  ## A starts higher or equal
        if (
            bboxA[1] <= bboxB[1]
        ):  ## B is completely in A; this can include height of B = 0:
            fraction = 1
        else:
            overlap = max(bboxB[3] - bboxA[1], 0)
            fraction = overlap / max(min_height, 0.001)
    else:
        if (
            bboxB[1] <= bboxA[1]
        ):  ## A is completely in B; this can include height of A = 0:
            fraction = 1
        else:
            overlap = max(bboxA[3] - bboxB[1], 0)
            fraction = overlap / max(min_height, 0.001)
    return fraction


## -------------------------------
## Cluster-and-cell relations


def compute_enclosed_cells(
    cluster_bbox, raw_cells, min_cell_intersection_with_cluster=0.2
):
    cells_in_cluster = []
    cells_in_cluster_int = []
    for ix, cell in enumerate(raw_cells):
        cell_bbox = cell["bbox"]
        intersection = compute_intersection(cell_bbox, cluster_bbox)
        frac_area = area(cell_bbox) * min_cell_intersection_with_cluster

        if (
            intersection > frac_area and frac_area > 0
        ):  # intersect > certain fraction of cell
            cells_in_cluster.append(ix)
            cells_in_cluster_int.append(intersection)
        elif contains(
            cluster_bbox,
            [cell_bbox[0] + 3, cell_bbox[1] + 3, cell_bbox[2] - 3, cell_bbox[3] - 3],
        ):
            cells_in_cluster.append(ix)
    return cells_in_cluster, cells_in_cluster_int


def find_clusters_around_cells(cell_count, clusters):
    ## Per raw cell, find to which clusters it belongs.
    ## Return list of these indices in the raw-cell order.
    clusters_around_cells = [[] for _ in range(cell_count)]
    for cl_ix, cluster in enumerate(clusters):
        for ix in cluster["cell_ids"]:
            clusters_around_cells[ix].append(cl_ix)
    return clusters_around_cells


def find_cell_index(raw_ix, cell_array):
    ## "raw_ix" is a rawcell_id.
    ## "cell_array" has the structure of an (annotation) cells array.
    ## Returns index of cell in cell_array that has this rawcell_id.
    for ix, cell in enumerate(cell_array):
        if cell["rawcell_id"] == raw_ix:
            return ix


def find_cell_indices(cluster, cell_array):
    ## "cluster" must have the structure as in a clusters array in a prediction,
    ## "cell_array" that of a cells array.
    ## Returns list of indices of cells in cell_array that have the rawcell_ids as in the cluster,
    ## in the order of the rawcell_ids.
    result = []
    for raw_ix in sorted(cluster["cell_ids"]):
        ## Find the cell with this rawcell_id (if any)
        for ix, cell in enumerate(cell_array):
            if cell["rawcell_id"] == raw_ix:
                result.append(ix)
    return result


def find_first_cell_index(cluster, cell_array):
    ## "cluster" must be a dict with key "cell_ids"; it can also be a line.
    ## "cell_array" has the structure of a cells array in an annotation.
    ## Returns index of cell in cell_array that has the lowest rawcell_id from the cluster.
    result = []  ## We keep it a list as it can be empty (picture without text cells)
    if len(cluster["cell_ids"]) == 0:
        return result
    raw_ix = min(cluster["cell_ids"])
    ## Find the cell with this rawcell_id (if any)
    for ix, cell in enumerate(cell_array):
        if cell["rawcell_id"] == raw_ix:
            result.append(ix)
            break  ## One is enough; should be only one anyway.
    if result == []:
        logger.debug(
            "  Warning: Raw cell " + str(raw_ix) + " not found in annotation cells"
        )
    return result


## -------------------------------
## Cluster labels and text


def relabel_cluster(cluster, cl_ix, new_label, target_pred):
    ## "cluster" must have the structure as in a clusters array in a prediction,
    ## "cl_ix" is its index in target_pred,
    ## "new_label" is the intended new label,
    ## "target_pred" is the entire current target prediction.
    ## Sets label on the cluster itself, and on the cells in the target_pred.
    ## Returns new_label so that also the cl_label variable in the main code is easily set.
    target_pred["clusters"][cl_ix]["type"] = new_label
    cluster_target_cells = find_cell_indices(cluster, target_pred["cells"])
    for ix in cluster_target_cells:
        target_pred["cells"][ix]["label"] = new_label
    return new_label


def find_cluster_text(cluster, raw_cells):
    ## "cluster" must be a dict with "cell_ids"; it can also be a line.
    ## "raw_cells" must have the format of item["raw"]["cells"]
    ## Returns the text of the cluster, with blanks between the cell contents
    ## (which seem to be words or phrases without starting or trailing blanks).
    ## Note that in formulas, this may give a lot more blanks than originally
    cluster_text = ""
    for raw_ix in sorted(cluster["cell_ids"]):
        cluster_text = cluster_text + raw_cells[raw_ix]["text"] + " "
    return cluster_text.rstrip()


def find_cluster_text_without_blanks(cluster, raw_cells):
    ## "cluster" must be a dict with "cell_ids"; it can also be a line.
    ## "raw_cells" must have the format of item["raw"]["cells"]
    ## Returns the text of the cluster, without blanks between the cell contents
    ## Interesting in formula analysis.
    cluster_text = ""
    for raw_ix in sorted(cluster["cell_ids"]):
        cluster_text = cluster_text + raw_cells[raw_ix]["text"]
    return cluster_text.rstrip()


## -------------------------------
## Clusters and lines
## (Most line-oriented functions are only needed in TextAnalysisGivenClusters,
##  but this one also in FormulaAnalysis)


def build_cluster_from_lines(lines, label, id):
    ## Lines must be a non-empty list of dicts (lines) with elements "cell_ids" and "bbox"
    ## (There is no condition that they are really geometrically lines)
    ## A cluster in standard format is returned with given label and id
    local_lines = copy.deepcopy(
        lines
    )  ## without this, it changes "lines" also outside this function
    first_line = local_lines.pop(0)
    cluster = {
        "id": id,
        "type": label,
        "cell_ids": first_line["cell_ids"],
        "bbox": first_line["bbox"],
        "confidence": 0,
        "created_by": "merged_cells",
    }
    confidence = 0
    counter = 0
    for line in local_lines:
        new_cell_ids = cluster["cell_ids"] + line["cell_ids"]
        cluster["cell_ids"] = new_cell_ids
        cluster["bbox"] = surrounding(cluster["bbox"], line["bbox"])
        counter += 1
        confidence += line["confidence"]
    confidence = confidence / counter
    cluster["confidence"] = confidence
    return cluster


## -------------------------------
## Reading order


def produce_reading_order(clusters, cluster_sort_type, cell_sort_type, sort_ids):
    ## In:
    ##   Clusters: list as in predictions.
    ##   cluster_sort_type: string, currently only "raw_cells".
    ##   cell_sort_type: string, currently only "raw_cells".
    ##   sort_ids: Boolean, whether the cluster ids should be adapted to their new position
    ## Out: Another clusters list, sorted according to the type.

    logger.debug("---- Start cluster sorting ------")

    if cell_sort_type == "raw_cell_ids":
        for cl in clusters:
            sorted_cell_ids = sorted(cl["cell_ids"])
            cl["cell_ids"] = sorted_cell_ids
    else:
        logger.debug(
            "Unknown cell_sort_type `"
            + cell_sort_type
            + "`, no cell sorting will happen."
        )

    if cluster_sort_type == "raw_cell_ids":
        clusters_with_cells = [cl for cl in clusters if cl["cell_ids"] != []]
        clusters_without_cells = [cl for cl in clusters if cl["cell_ids"] == []]
        logger.debug(
            "Clusters with cells: " + str([cl["id"] for cl in clusters_with_cells])
        )
        logger.debug(
            "  Their first cell ids: "
            + str([cl["cell_ids"][0] for cl in clusters_with_cells])
        )
        logger.debug(
            "Clusters without cells: "
            + str([cl["id"] for cl in clusters_without_cells])
        )
        clusters_with_cells_sorted = sorted(
            clusters_with_cells, key=lambda cluster: cluster["cell_ids"][0]
        )
        logger.debug(
            "  First cell ids after sorting: "
            + str([cl["cell_ids"][0] for cl in clusters_with_cells_sorted])
        )
        sorted_clusters = clusters_with_cells_sorted + clusters_without_cells
    else:
        logger.debug(
            "Unknown cluster_sort_type: `"
            + cluster_sort_type
            + "`, no cluster sorting will happen."
        )

    if sort_ids:
        for i, cl in enumerate(sorted_clusters):
            cl["id"] = i
    return sorted_clusters


## -------------------------------
## Line Splitting


def sort_cells_horizontal(line_cell_ids, raw_cells):
    ## "line_cells" should be a non-empty list of (raw) cell_ids
    ## "raw_cells" has the structure of item["raw"]["cells"].
    ## Sorts the cells in the line by x0 (left start).
    new_line_cell_ids = sorted(
        line_cell_ids, key=lambda cell_id: raw_cells[cell_id]["bbox"][0]
    )
    return new_line_cell_ids


def adapt_bboxes(raw_cells, clusters, orphan_cell_indices):
    new_clusters = []
    for ix, cluster in enumerate(clusters):
        new_cluster = copy.deepcopy(cluster)
        logger.debug(
            "Treating cluster " + str(ix) + ", type " + str(new_cluster["type"])
        )
        logger.debug("  with cells: " + str(new_cluster["cell_ids"]))
        if len(cluster["cell_ids"]) == 0 and cluster["type"] != "Picture":
            logger.debug("  Empty non-picture, removed")
            continue  ## Skip this former cluster, now without cells.
        new_bbox = adapt_bbox(raw_cells, new_cluster, orphan_cell_indices)
        new_cluster["bbox"] = new_bbox
        new_clusters.append(new_cluster)
    return new_clusters


def adapt_bbox(raw_cells, cluster, orphan_cell_indices):
    if not (cluster["type"] in ["Table", "Picture"]):
        ## A text-like cluster. The bbox only needs to be around the text cells:
        logger.debug("    Initial bbox: " + str(cluster["bbox"]))
        new_bbox = surrounding_list(
            [raw_cells[cid]["bbox"] for cid in cluster["cell_ids"]]
        )
        logger.debug("  New bounding box:" + str(new_bbox))
    if cluster["type"] == "Picture":
        ## We only make the bbox completely comprise included text cells:
        logger.debug("  Picture")
        if len(cluster["cell_ids"]) != 0:
            min_bbox = surrounding_list(
                [raw_cells[cid]["bbox"] for cid in cluster["cell_ids"]]
            )
            logger.debug("    Minimum bbox: " + str(min_bbox))
            logger.debug("    Initial bbox: " + str(cluster["bbox"]))
            new_bbox = surrounding(min_bbox, cluster["bbox"])
            logger.debug("    New bbox (initial and text cells): " + str(new_bbox))
        else:
            logger.debug("    without text cells, no change.")
            new_bbox = cluster["bbox"]
    else:  ## A table
        ## At least we have to keep the included text cells, and we make the bbox completely comprise them
        min_bbox = surrounding_list(
            [raw_cells[cid]["bbox"] for cid in cluster["cell_ids"]]
        )
        logger.debug("    Minimum bbox: " + str(min_bbox))
        logger.debug("    Initial bbox: " + str(cluster["bbox"]))
        new_bbox = surrounding(min_bbox, cluster["bbox"])
        logger.debug("    Possibly increased bbox: " + str(new_bbox))

        ## Now we look which non-belonging cells are covered.
        ## (To decrease dependencies, we don't make use of which cells we actually removed.)
        ## We don't worry about orphan cells, those could still be added to the table.
        enclosed_cells = compute_enclosed_cells(
            new_bbox, raw_cells, min_cell_intersection_with_cluster=0.3
        )[0]
        additional_cells = set(enclosed_cells) - set(cluster["cell_ids"])
        logger.debug(
            "    Additional cells enclosed by Table bbox: " + str(additional_cells)
        )
        spurious_cells = additional_cells - set(orphan_cell_indices)
        logger.debug(
            "    Spurious cells enclosed by Table bbox (additional minus orphans): "
            + str(spurious_cells)
        )
        if len(spurious_cells) == 0:
            return new_bbox

        ## Else we want to keep as much as possible, e.g., grid lines, but not the spurious cells if we can.
        ## We initialize possible cuts with the current bbox.
        left_cut = new_bbox[0]
        right_cut = new_bbox[2]
        upper_cut = new_bbox[3]
        lower_cut = new_bbox[1]

        for cell_ix in spurious_cells:
            cell = raw_cells[cell_ix]
            # logger.debug("     Spurious cell bbox: " + str(cell["bbox"]))
            is_left = cell["bbox"][2] < min_bbox[0]
            is_right = cell["bbox"][0] > min_bbox[2]
            is_above = cell["bbox"][1] > min_bbox[3]
            is_below = cell["bbox"][3] < min_bbox[1]
            # logger.debug("      Left, right, above, below? " + str([is_left, is_right, is_above, is_below]))

            if is_left:
                if cell["bbox"][2] > left_cut:
                    ## We move the left cut to exclude this cell:
                    left_cut = cell["bbox"][2]
            if is_right:
                if cell["bbox"][0] < right_cut:
                    ## We move the right cut to exclude this cell:
                    right_cut = cell["bbox"][0]
            if is_above:
                if cell["bbox"][1] < upper_cut:
                    ## We move the upper cut to exclude this cell:
                    upper_cut = cell["bbox"][1]
            if is_below:
                if cell["bbox"][3] > lower_cut:
                    ## We move the left cut to exclude this cell:
                    lower_cut = cell["bbox"][3]
            # logger.debug("      Current bbox: " + str([left_cut, lower_cut, right_cut, upper_cut]))

            new_bbox = [left_cut, lower_cut, right_cut, upper_cut]

        logger.debug("   Final bbox: " + str(new_bbox))
    return new_bbox


def remove_cluster_duplicates_by_conf(cluster_predictions, threshold=0.5):
    DuplicateDeletedClusterIDs = []
    for cluster_1 in cluster_predictions:
        for cluster_2 in cluster_predictions:
            if cluster_1["id"] != cluster_2["id"]:
                if_conf = False
                if cluster_1["confidence"] > cluster_2["confidence"]:
                    if_conf = True
                if if_conf == True:
                    if bb_iou(cluster_1["bbox"], cluster_2["bbox"]) > threshold:
                        DuplicateDeletedClusterIDs.append(cluster_2["id"])
                    elif contains(
                        cluster_1["bbox"],
                        [
                            cluster_2["bbox"][0] + 3,
                            cluster_2["bbox"][1] + 3,
                            cluster_2["bbox"][2] - 3,
                            cluster_2["bbox"][3] - 3,
                        ],
                    ):
                        DuplicateDeletedClusterIDs.append(cluster_2["id"])

    DuplicateDeletedClusterIDs = list(set(DuplicateDeletedClusterIDs))

    for cl_id in DuplicateDeletedClusterIDs:
        for cluster in cluster_predictions:
            if cl_id == cluster["id"]:
                cluster_predictions.remove(cluster)
    return cluster_predictions


# Assign orphan cells by a low confidence prediction that is below the assigned confidence
def assign_orphans_with_low_conf_pred(
    cluster_predictions, cluster_predictions_low, raw_cells, orphan_cell_indices
):
    for orph_id in orphan_cell_indices:
        cluster_chosen = {}
        iou_thresh = 0.05
        confidence = 0.05

        # Loop over all predictions, and find the one with the highest IOU, and confidence
        for cluster in cluster_predictions_low:
            calc_iou = bb_iou(cluster["bbox"], raw_cells[orph_id]["bbox"])
            cluster_area = (cluster["bbox"][3] - cluster["bbox"][1]) * (
                cluster["bbox"][2] - cluster["bbox"][0]
            )
            cell_area = (
                raw_cells[orph_id]["bbox"][3] - raw_cells[orph_id]["bbox"][1]
            ) * (raw_cells[orph_id]["bbox"][2] - raw_cells[orph_id]["bbox"][0])

            if (
                (iou_thresh < calc_iou)
                and (cluster["confidence"] > confidence)
                and (cell_area * 3 > cluster_area)
            ):
                cluster_chosen = cluster
                iou_thresh = calc_iou
                confidence = cluster["confidence"]
        # If a candidate is found, assign to it the PDF cell ids, and tag that it was created by this function for tracking
        if iou_thresh != 0.05 and confidence != 0.05:
            cluster_chosen["cell_ids"].append(orph_id)
            cluster_chosen["created_by"] = "orph_low_conf"
            cluster_predictions.append(cluster_chosen)
            orphan_cell_indices.remove(orph_id)
    return cluster_predictions, orphan_cell_indices


def remove_ambigous_pdf_cell_by_conf(cluster_predictions, raw_cells, amb_cell_idxs):
    for amb_cell_id in amb_cell_idxs:
        highest_conf = 0
        highest_bbox_iou = 0
        cluster_chosen = None
        problamatic_clusters = []

        # Find clusters in question
        for cluster in cluster_predictions:

            if amb_cell_id in cluster["cell_ids"]:
                problamatic_clusters.append(amb_cell_id)

                # If the cell_id is in a cluster of high conf, and highest iou score, and smaller in area
                bbox_iou_val = bb_iou(cluster["bbox"], raw_cells[amb_cell_id]["bbox"])

                if (
                    cluster["confidence"] > highest_conf
                    and bbox_iou_val > highest_bbox_iou
                ):
                    cluster_chosen = cluster
                    highest_conf = cluster["confidence"]
                    highest_bbox_iou = bbox_iou_val
                    if cluster["id"] in problamatic_clusters:
                        problamatic_clusters.remove(cluster["id"])

        # now remove the assigning of cell id from lower confidence, and threshold
        for cluster in cluster_predictions:
            for prob_amb_id in problamatic_clusters:
                if prob_amb_id in cluster["cell_ids"]:
                    cluster["cell_ids"].remove(prob_amb_id)
        amb_cell_idxs.remove(amb_cell_id)

    return cluster_predictions, amb_cell_idxs


def ranges(nums):
    # Find if consecutive numbers exist within pdf cells
    # Used to remove line numbers for review manuscripts
    nums = sorted(set(nums))
    gaps = [[s, e] for s, e in zip(nums, nums[1:]) if s + 1 < e]
    edges = iter(nums[:1] + sum(gaps, []) + nums[-1:])
    return list(zip(edges, edges))


def set_orphan_as_text(
    cluster_predictions, cluster_predictions_low, raw_cells, orphan_cell_indices
):
    max_id = -1
    figures = []
    for cluster in cluster_predictions:
        if cluster["type"] == "Picture":
            figures.append(cluster)

        if cluster["id"] > max_id:
            max_id = cluster["id"]
    max_id += 1

    lines_detector = False
    content_of_orphans = []
    for orph_id in orphan_cell_indices:
        orph_cell = raw_cells[orph_id]
        content_of_orphans.append(raw_cells[orph_id]["text"])

    fil_content_of_orphans = []
    for cell_content in content_of_orphans:
        if cell_content.isnumeric():
            try:
                num = int(cell_content)
                fil_content_of_orphans.append(num)
            except ValueError:  # ignore the cell
                pass

    # line_orphans = []
    #  Check if there are more than 2 pdf orphan cells, if there are more than 2,
    #  then check between the orphan cells if they are numeric
    # and if they are a consecutive series of numbers (using ranges function) to decide

    if len(fil_content_of_orphans) > 2:
        out_ranges = ranges(fil_content_of_orphans)
        if len(out_ranges) > 1:
            cnt_range = 0
            for ranges_ in out_ranges:
                if ranges_[0] != ranges_[1]:
                    # If there are more than 75 (half the total line number of a review manuscript page)
                    # decide that there are line numbers on page to be ignored.
                    if len(list(range(ranges_[0], ranges_[1]))) > 75:
                        lines_detector = True
                        # line_orphans = line_orphans + list(range(ranges_[0], ranges_[1]))

    for orph_id in orphan_cell_indices:
        orph_cell = raw_cells[orph_id]
        if bool(orph_cell["text"] and not orph_cell["text"].isspace()):
            fig_flag = False
            # Do not assign orphan cells if they are inside a figure
            for fig in figures:
                if contains(fig["bbox"], orph_cell["bbox"]):
                    fig_flag = True

            # if fig_flag == False and raw_cells[orph_id]["text"] not in line_orphans:
            if fig_flag == False and lines_detector == False:
                # get class from low confidence detections if not set as text:
                class_type = "Text"

                for cluster in cluster_predictions_low:
                    intersection = compute_intersection(
                        orph_cell["bbox"], cluster["bbox"]
                    )
                    class_type = "Text"
                    if (
                        cluster["confidence"] > 0.1
                        and bb_iou(cluster["bbox"], orph_cell["bbox"]) > 0.4
                    ):
                        class_type = cluster["type"]
                    elif contains(
                        cluster["bbox"],
                        [
                            orph_cell["bbox"][0] + 3,
                            orph_cell["bbox"][1] + 3,
                            orph_cell["bbox"][2] - 3,
                            orph_cell["bbox"][3] - 3,
                        ],
                    ):
                        class_type = cluster["type"]
                    elif intersection > area(orph_cell["bbox"]) * 0.2:
                        class_type = cluster["type"]

                new_cluster = {
                    "id": max_id,
                    "bbox": orph_cell["bbox"],
                    "type": class_type,
                    "cell_ids": [orph_id],
                    "confidence": -1,
                    "created_by": "orphan_default",
                }
                max_id += 1
                cluster_predictions.append(new_cluster)
    return cluster_predictions, orphan_cell_indices


def merge_cells(cluster_predictions):
    # Using graph component creates clusters if orphan cells are touching or too close.
    G = nx.Graph()
    for cluster in cluster_predictions:
        if cluster["created_by"] == "orphan_default":
            G.add_node(cluster["id"])

    for cluster_1 in cluster_predictions:
        for cluster_2 in cluster_predictions:
            if (
                cluster_1["id"] != cluster_2["id"]
                and cluster_2["created_by"] == "orphan_default"
                and cluster_1["created_by"] == "orphan_default"
            ):
                cl1 = copy.deepcopy(cluster_1["bbox"])
                cl2 = copy.deepcopy(cluster_2["bbox"])
                cl1[0] = cl1[0] - 2
                cl1[1] = cl1[1] - 2
                cl1[2] = cl1[2] + 2
                cl1[3] = cl1[3] + 2
                cl2[0] = cl2[0] - 2
                cl2[1] = cl2[1] - 2
                cl2[2] = cl2[2] + 2
                cl2[3] = cl2[3] + 2
                if is_intersecting(cl1, cl2):
                    G.add_edge(cluster_1["id"], cluster_2["id"])

    component = sorted(map(sorted, nx.k_edge_components(G, k=1)))
    max_id = -1
    for cluster_1 in cluster_predictions:
        if cluster_1["id"] > max_id:
            max_id = cluster_1["id"]

    for nodes in component:
        if len(nodes) > 1:
            max_id += 1
            lines = []
            for node in nodes:
                for cluster in cluster_predictions:
                    if cluster["id"] == node:
                        lines.append(cluster)
                        cluster_predictions.remove(cluster)
            new_merged_cluster = build_cluster_from_lines(lines, "Text", max_id)
            cluster_predictions.append(new_merged_cluster)
    return cluster_predictions


def clean_up_clusters(
    cluster_predictions,
    raw_cells,
    merge_cells=False,
    img_table=False,
    one_cell_table=False,
):
    DuplicateDeletedClusterIDs = []

    for cluster_1 in cluster_predictions:
        for cluster_2 in cluster_predictions:
            if cluster_1["id"] != cluster_2["id"]:
                # remove any artifcats created by merging clusters
                if merge_cells == True:
                    if contains(
                        cluster_1["bbox"],
                        [
                            cluster_2["bbox"][0] + 3,
                            cluster_2["bbox"][1] + 3,
                            cluster_2["bbox"][2] - 3,
                            cluster_2["bbox"][3] - 3,
                        ],
                    ):
                        cluster_1["cell_ids"] = (
                            cluster_1["cell_ids"] + cluster_2["cell_ids"]
                        )
                        DuplicateDeletedClusterIDs.append(cluster_2["id"])
                # remove clusters that might appear inside tables, or images (such as pdf cells in graphs)
                elif img_table == True:
                    if (
                        cluster_1["type"] == "Text"
                        and cluster_2["type"] == "Picture"
                        or cluster_2["type"] == "Table"
                    ):
                        if bb_iou(cluster_1["bbox"], cluster_2["bbox"]) > 0.5:
                            DuplicateDeletedClusterIDs.append(cluster_1["id"])
                        elif contains(
                            [
                                cluster_2["bbox"][0] - 3,
                                cluster_2["bbox"][1] - 3,
                                cluster_2["bbox"][2] + 3,
                                cluster_2["bbox"][3] + 3,
                            ],
                            cluster_1["bbox"],
                        ):
                            DuplicateDeletedClusterIDs.append(cluster_1["id"])
            # remove tables that have one pdf cell
            if one_cell_table == True:
                if cluster_1["type"] == "Table" and len(cluster_1["cell_ids"]) < 2:
                    DuplicateDeletedClusterIDs.append(cluster_1["id"])

    DuplicateDeletedClusterIDs = list(set(DuplicateDeletedClusterIDs))

    for cl_id in DuplicateDeletedClusterIDs:
        for cluster in cluster_predictions:
            if cl_id == cluster["id"]:
                cluster_predictions.remove(cluster)
    return cluster_predictions


def assigning_cell_ids_to_clusters(clusters, raw_cells, threshold):
    for cluster in clusters:
        cells_in_cluster, _ = compute_enclosed_cells(
            cluster["bbox"], raw_cells, min_cell_intersection_with_cluster=threshold
        )
        cluster["cell_ids"] = cells_in_cluster
        ## These cell_ids are ids of the raw cells.
        ## They are often, but not always, the same as the "id" or the index of the "cells" list in a prediction.
    return clusters


# Creates a map of cell_id->cluster_id
def cell_id_state_map(clusters, cell_count):
    clusters_around_cells = find_clusters_around_cells(cell_count, clusters)
    orphan_cell_indices = [
        ix for ix in range(cell_count) if len(clusters_around_cells[ix]) == 0
    ]  # which cells are assigned no cluster?
    ambiguous_cell_indices = [
        ix for ix in range(cell_count) if len(clusters_around_cells[ix]) > 1
    ]  # which cells are assigned > 1 clusters?
    return clusters_around_cells, orphan_cell_indices, ambiguous_cell_indices
