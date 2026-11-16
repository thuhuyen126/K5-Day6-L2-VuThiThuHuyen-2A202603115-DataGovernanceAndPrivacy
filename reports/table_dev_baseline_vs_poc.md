# T02 DEV: Global Laplacian Baseline vs Blur/Dark PoC V1

## Protocol

- Split: DEV only (56 images)
- Review budget: B=20
- Baseline: one global Laplacian threshold across all cameras/lights
- PoC: max(blur_score, dark_score), with DEV-only Blur references
- No ground-truth labels used

## Global Laplacian baseline

- Global threshold (20th lowest Laplacian value): 326.281647
- Top-20 candidates: 20

## Ranking overlap

- Shared images: 16/20
- Jaccard similarity: 0.6667

## Baseline top-20

```text
image_id       score camera_id light
img_09_2   -1.661736     cam_B   day
img_21_2   -1.786935     cam_B   day
img_18_3   -1.818989     cam_B night
img_04_3   -3.406475     cam_A  dusk
img_07_3   -4.615544     cam_A   day
img_11_3   -4.796146     cam_A   day
img_14_2   -5.779385     cam_A   day
img_00_3   -5.961263     cam_B   day
img_12_3  -42.809013     cam_B  dusk
img_12_0 -166.382172     cam_B  dusk
img_12_2 -182.545212     cam_B  dusk
img_09_0 -186.966599     cam_B   day
img_09_3 -196.096191     cam_B   day
img_21_0 -220.705276     cam_B   day
img_07_2 -222.847855     cam_A   day
img_21_3 -250.826950     cam_B   day
img_08_3 -264.077057     cam_A  dusk
img_00_0 -266.882965     cam_B   day
img_02_3 -290.551086     cam_A   day
img_10_3 -326.281647     cam_A   day
```

## PoC top-20

```text
image_id camera_id light split       blur  blur_score blur_reference  frac_dark  brightness  dark_score    score
img_07_3     cam_A   day   dev   4.615544    0.958333   camera_light   0.000139  122.225151    0.000000 0.958333
img_08_3     cam_A  dusk   dev 264.077057    0.833333   camera_light   0.936927   13.682333    0.936927 0.936927
img_04_3     cam_A  dusk   dev   3.406475    0.916667   camera_light   0.000035   88.321579    0.000000 0.916667
img_09_2     cam_B   day   dev   1.661736    0.916667   camera_light   0.000000  114.501442    0.000000 0.916667
img_11_3     cam_A   day   dev   4.796146    0.916667   camera_light   0.000000  125.812881    0.000000 0.916667
img_12_3     cam_B  dusk   dev  42.809013    0.750000         camera   0.897587   12.861792    0.897587 0.897587
img_14_2     cam_A   day   dev   5.779385    0.875000   camera_light   0.000000  123.671043    0.000000 0.875000
img_18_3     cam_B night   dev   1.818989    0.850000         camera   0.576979   32.446579    0.422113 0.850000
img_07_2     cam_A   day   dev 222.847855    0.833333   camera_light   0.698073   25.976336    0.580192 0.833333
img_21_2     cam_B   day   dev   1.786935    0.833333   camera_light   0.000000  120.661217    0.000000 0.833333
img_02_3     cam_A   day   dev 290.551086    0.791667   camera_light   0.752326   23.937332    0.648883 0.791667
img_00_3     cam_B   day   dev   5.961263    0.750000   camera_light   0.000000  118.423370    0.000000 0.750000
img_08_2     cam_A  dusk   dev 478.906311    0.750000   camera_light   0.001024   90.702774    0.000000 0.750000
img_10_3     cam_A   day   dev 326.281647    0.750000   camera_light   0.730451   24.456030    0.624187 0.750000
img_20_2     cam_A   day   dev 376.078369    0.708333   camera_light   0.740035   23.403204    0.644363 0.708333
img_12_0     cam_B  dusk   dev 166.382172    0.700000         camera   0.000382   88.647087    0.000000 0.700000
img_04_2     cam_A  dusk   dev 498.041626    0.666667   camera_light   0.002031   87.902260    0.000000 0.666667
img_09_0     cam_B   day   dev 186.966599    0.666667   camera_light   0.000191  114.581161    0.000000 0.666667
img_11_2     cam_A   day   dev 676.341431    0.666667   camera_light   0.002101  125.513634    0.000000 0.666667
img_12_2     cam_B  dusk   dev 182.545212    0.650000         camera   0.000451   88.140518    0.000000 0.650000
```

## Camera/light composition

### Baseline

```text
camera_id light  count
    cam_A   day      6
    cam_A  dusk      2
    cam_B   day      8
    cam_B  dusk      3
    cam_B night      1
```

### PoC

```text
camera_id light  count
    cam_A   day      8
    cam_A  dusk      4
    cam_B   day      4
    cam_B  dusk      3
    cam_B night      1
```

## Interpretation limitation

This is an unlabeled DEV ranking comparison, not a defect-recall or precision evaluation. Ground-truth labels are required for Defect Recall@20 and Precision@20.

## Analysis and failure-mode observations

### Baseline vs PoC

Both methods rank 20 images from the same DEV split.

The two rankings share 16 images, with a Jaccard similarity of
0.6667. This indicates substantial but not identical overlap.

The global Laplacian baseline selects 12 cam_B images and 8 cam_A
images. The Blur/Dark PoC selects 8 cam_B images and 12 cam_A images.

This difference suggests that camera-aware Blur references may
reduce the influence of camera-specific optical characteristics.
However, this is an unlabeled DEV comparison and does not establish
that the PoC has higher defect-detection accuracy.

### Mandatory failure modes

1. Useful night images:
   One night image, img_18_3, appears in both top-20 rankings.
   It requires cautious interpretation because its Blur and Dark
   signals overlap. The other night images should not be automatically
   classified as defective based on lighting alone.

2. Localized glare:
   The current Blur/Dark PoC does not implement a dedicated local
   glare detector. This failure mode requires a separate Glare
   feature and human inspection.

3. Camera-specific optical differences:
   The baseline selects more cam_B images than the PoC (12 vs 8).
   Camera-aware reference distributions may mitigate this bias,
   but further validation with ground-truth labels is required.

### Evaluation limitation

These results describe ranking behavior on DEV only.
They are not Defect Recall@20 or Precision@20 measurements.
No ground-truth labels were used for this comparison.