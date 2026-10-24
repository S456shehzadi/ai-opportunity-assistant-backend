"""Exact and near-duplicate webpage detection using content hashing and SimHash."""

import hashlib
import re

TOKEN_SPLIT_RE = re.compile(r"\w+")


class DuplicateDetector:
    """Detects exact and near-duplicate documents across web crawls."""

    @classmethod
    def compute_content_hash(cls, text: str) -> str:
        """Computes SHA-256 hash of normalized text for exact duplicate detection."""
        words = TOKEN_SPLIT_RE.findall(text.lower())
        normalized = " ".join(words)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def compute_simhash(cls, text: str) -> str:
        """Computes a 64-bit SimHash hex string for near-duplicate detection."""
        words = TOKEN_SPLIT_RE.findall(text.lower())
        if not words:
            return "0000000000000000"

        # 64-dimension vector
        v = [0] * 64

        for word in words:
            # 64-bit hash of token
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:16], 16)
            for i in range(64):
                bitmask = 1 << i
                if h & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(64):
            if v[i] > 0:
                fingerprint |= 1 << i

        return f"{fingerprint:016x}"

    @classmethod
    def is_exact_duplicate(cls, hash1: str, hash2: str) -> bool:
        """Checks if two documents have identical SHA-256 content hashes."""
        return bool(hash1 and hash2 and hash1 == hash2)

    @classmethod
    def is_near_duplicate(
        cls,
        simhash1: str,
        simhash2: str,
        max_hamming_distance: int = 6,
    ) -> bool:
        """Checks if two documents are near-duplicates using SimHash Hamming distance.

        A Hamming distance <= 6 typically indicates identical content with minor alterations
        (e.g., changed timestamps, navigation updates, or minor typo edits).
        """
        if not simhash1 or not simhash2:
            return False

        try:
            num1 = int(simhash1, 16)
            num2 = int(simhash2, 16)
        except ValueError:
            return False

        # XOR and count set bits
        xor_val = num1 ^ num2
        distance = bin(xor_val).count("1")

        return distance <= max_hamming_distance

    @classmethod
    def compute_jaccard_similarity(cls, text1: str, text2: str, n: int = 3) -> float:
        """Computes n-gram word shingle Jaccard similarity between two texts."""
        words1 = TOKEN_SPLIT_RE.findall(text1.lower())
        words2 = TOKEN_SPLIT_RE.findall(text2.lower())

        if not words1 or not words2:
            return 0.0

        shingles1 = {tuple(words1[i : i + n]) for i in range(len(words1) - n + 1)}
        shingles2 = {tuple(words2[i : i + n]) for i in range(len(words2) - n + 1)}

        if not shingles1 or not shingles2:
            return 0.0

        intersection = len(shingles1 & shingles2)
        union = len(shingles1 | shingles2)

        return round(intersection / union, 4) if union > 0 else 0.0
