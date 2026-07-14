from jiwer import wer, cer

ground_truth = """Example:
Strings:
["Islamabad Highway", "Islamabad G-10", "Islamabad G-11"]
Split →
["Islamabad Highway", "Islamabad ..."]
return Merge(leftHull(), rightHull())
Merge(L, R):
Find upper tangent of L and R
Find lower tangent of L and R
Combine to form merged hull
Edge Cases:
Collinear points → Keep only endpoints of the collinear segment.
Duplicate points → Remove before processing.
Time Complexity:
T(n) = 2T(n/2) + O(n) → O(n log n)
Benefit for drones: Convex hull defines the minimal flight boundary around crop clusters, so drones avoid obstacles and cover the area efficiently in real-time.
QUESTION NO #03
Matrix Multiplication
Idea: Split each (n x n) matrix into four ((n/2) x (n/2)) submatrices, recursively multiply, then combine.
Partition:
A = | A11  A12 |      B = | B11  B12 |
    | A21  A22 |          | B21  B22 |"""

extracted = """i=0
while i<len(s1) and i<len(s2) and s1[i]==s2[i]:
    i++
return s1[0...i-1].
2 of 20 d Example:
us: ['Islamabad Highway', 'Islamabad G-10', 'Islamabad G-11']
split→ ['Islamabad Highway', 'Islamabad
return Merge(leftHull,rightHull)
Merge(L ,R): 
Find upper tangent of L and R : 
-Find lower tangent of L and R 
Combine to form merged hull.
Edge Cases:
- Collinear points → keep only endpoints 
of the collinear Segment
- Duplicate points → remove before processing 
Time Complexity: T(n) = 2T (n/2) +0(n) →0(nlogn)
Benefit for chosen Convex hull defines 
the minimal flight boundary around 
a crop cluster, so drones avoid 
obstacles and cover the area 
efficiently. In real-time 
the minimal flight 
QUESTION NO#03
MATRIX MULTIPLICATION:
Idea: 
split each nxn matrix into four 
(n/2) x (n/2) submatrices, recursively multiply 
then combine.
Partition:
A = [A11      A12]   B = [B11      B12]
    [A21      A22]       [B21      B22]"""

word_error_rate = wer(ground_truth, extracted)
char_error_rate = cer(ground_truth, extracted)

print("Ground truth length:", len(ground_truth))
print("Extracted length:", len(extracted))
print()
print(f"Word Error Rate: {word_error_rate:.2%}")
print(f"Character Error Rate: {char_error_rate:.2%}")
print(f"Word Accuracy: {(1 - word_error_rate):.2%}")
print(f"Character Accuracy: {(1 - char_error_rate):.2%}")