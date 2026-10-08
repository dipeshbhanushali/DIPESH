"""
Telling populations of spots apart.

    separation   separation_score, best_threshold
    pca          pca, spot_matrix, ellipse_points
"""

from .separation import separation_score, best_threshold
from .pca import pca, spot_matrix, ellipse_points
