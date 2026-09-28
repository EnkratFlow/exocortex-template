"""Offline memory pilot checks; optional real GEPA uses fake model callables."""
import copy
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.exocortex/scripts'))
import memory_gepa as pilot
import curate_memory


def budget(readers=100, reflectors=10, approved='100'):
    return pilot.Budget(Decimal(approved), Decimal('0.01'), Decimal('0.02'), readers, reflectors)


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.train = pilot.load_cases(pilot.CASES, 'train')
        self.validation = pilot.load_cases(pilot.CASES, 'validation')

    def test_reference_scores_and_disjoint_splits(self):
        splits = [self.train, self.validation, pilot.load_cases(pilot.CASES, 'holdout')]
        ids, histories = set(), set()
        for split in splits:
            for case in split:
                self.assertNotIn(case['id'], ids)
                digest = curate_memory.fingerprint(case['events'])
                self.assertNotIn(digest, histories)
                ids.add(case['id']); histories.add(digest)
                self.assertEqual(pilot.score(case, case['expected'])['score'], 1)

    def test_wrong_status_and_forged_quote_fail(self):
        case = self.train[0]
        reply = copy.deepcopy(case['expected'])
        reply['items'][0]['status'] = 'closed'
        self.assertEqual(pilot.score(case, reply)['score'], 0)
        reply['items'][0]['evidence'][0]['quote'] = 'fabricated source text'
        self.assertTrue(pilot.score(case, reply)['hard_failure'])
        for response in ('bad json', {'items': [{'status': []}]}, {'items': [], 'extra': True}):
            self.assertTrue(pilot.score(case, response)['hard_failure'])

    def test_additional_verbatim_context_is_allowed_but_decisive_source_required(self):
        case = self.train[0]
        reply = copy.deepcopy(case['expected'])
        reply['items'][0]['evidence'].append({'event': 'e1', 'quote': case['events'][0]['body']})
        self.assertEqual(pilot.score(case, reply)['score'], 1)
        reply['items'][0]['evidence'] = reply['items'][0]['evidence'][1:]
        self.assertEqual(pilot.score(case, reply)['score'], 0)

    def test_identifier_wording_is_separate_from_disposition(self):
        case = self.train[0]
        reply = copy.deepcopy(case['expected'])
        reply['items'][0]['key'] = 'cache_release_status'
        result = pilot.score(case, reply)
        self.assertEqual(result['score'], 1)
        self.assertEqual(result['identifier_matches'], 0)
        extra = copy.deepcopy(reply['items'][0]); extra['key'] = 'duplicate'
        reply['items'].append(extra)
        self.assertAlmostEqual(pilot.score(case, reply)['score'], 2/3)

    def test_budget_reserved_on_failure_and_stops_before_invoking(self):
        value = budget(approved='0.01')
        calls = []
        def fail(cap):
            calls.append(cap)
            raise RuntimeError('fake provider failure')
        with self.assertRaises(RuntimeError): value.call('reader', fail)
        with self.assertRaises(pilot.BudgetStop): value.call('reader', fail)
        self.assertEqual(len(calls), 1)
        self.assertEqual(value.reserved, Decimal('0.01'))

    def test_split_overlap_refused(self):
        with self.assertRaises(ValueError): pilot.Adapter(self.train, self.train, None, budget())
        cloned = copy.deepcopy(self.train[0]); cloned['id'] = 'different-id'
        with self.assertRaises(ValueError): pilot.Adapter(self.train, [cloned], None, budget())

    def test_holdout_requires_improvement_and_never_promotes(self):
        cases = pilot.load_cases(pilot.CASES, 'holdout')
        answers = {curate_memory.fingerprint(c['events']): c['expected'] for c in cases}
        def reader(prompt, events, cap):
            return answers[curate_memory.fingerprint(events)] if prompt == 'candidate' else {'items': []}
        report = pilot.evaluate_holdout(reader, budget(), 'baseline', 'candidate')
        self.assertTrue(report['review_candidate'])
        self.assertFalse(report['promoted'])
        self.assertNotIn('feedback', report)
        tied = pilot.evaluate_holdout(reader, budget(), 'candidate', 'candidate')
        self.assertFalse(tied['review_candidate'])
        self.assertTrue(tied['identical_prompts'])

    @unittest.skipUnless(importlib.util.find_spec('gepa'), 'optional GEPA not installed')
    def test_reader_never_gets_key_and_reflection_only_training(self):
        calls = []
        def reader(prompt, events, cap):
            calls.append(events)
            self.assertTrue(all(set(e) == {'name', 'body'} for e in events))
            return {'items': []}
        adapter = pilot.Adapter(self.train, self.validation, reader, budget())
        candidate = {'curator': 'prompt'}
        batch = adapter.evaluate([{'id': self.train[0]['id']}], candidate, True)
        adapter.evaluate([{'id': self.train[0]['id']}], candidate)
        self.assertEqual(len(calls), 1)
        self.assertIn('reference', adapter.make_reflective_dataset(candidate, batch, ['curator'])['curator'][0]['Feedback'])
        selected = adapter.evaluate([{'id': self.validation[0]['id']}], candidate, True)
        with self.assertRaises(ValueError): adapter.make_reflective_dataset(candidate, selected, ['curator'])
        with self.assertRaises(ValueError): adapter.evaluate([{'id': 'held-out-unknown'}], candidate)

    @unittest.skipUnless(importlib.util.find_spec('gepa'), 'optional GEPA not installed')
    def test_real_gepa_with_fake_bridges_does_not_load_holdout(self):
        answers = {curate_memory.fingerprint(c['events']): c['expected'] for c in self.train + self.validation}
        original = pilot.load_cases
        def loader(folder, split):
            self.assertNotEqual(split, 'holdout')
            return original(folder, split)
        def reader(prompt, events, cap):
            return answers[curate_memory.fingerprint(events)] if prompt == 'improved' else {'items': []}
        with patch.object(pilot, 'load_cases', loader):
            result = pilot.optimize(reader, lambda prompt, cap: '```\nimproved\n```', budget(readers=40, reflectors=1), seed_prompt='baseline')
        self.assertEqual(result['status'], 'development_only')
        self.assertEqual(result['candidate'], 'improved')
        self.assertFalse(result['promoted'])
        self.assertGreater(result['reflection_calls'], 0)
        self.assertEqual(result['reflection_calls'], 1)
        self.assertLessEqual(result['reader_calls'], 40)

    @unittest.skipUnless(importlib.util.find_spec('gepa'), 'optional GEPA not installed')
    def test_real_gepa_budget_stop_returns_no_candidate(self):
        result = pilot.optimize(lambda *args: {'items': []}, lambda *args: 'unused', budget(approved='0.01'), seed_prompt='baseline')
        self.assertEqual(result['status'], 'stopped')
        self.assertIsNone(result['candidate'])
        self.assertEqual(result['reader_calls'], 1)

    @unittest.skipUnless(importlib.util.find_spec('gepa'), 'optional GEPA not installed')
    def test_structured_answers_are_rejected_as_a_prompt(self):
        result = pilot.optimize(lambda *args: {'items': []},
                                lambda *args: '```json\n{"items": []}\n```',
                                budget(reflectors=1), seed_prompt='baseline')
        self.assertEqual(result['status'], 'proposal_rejected')
        self.assertEqual(result['candidate'], 'baseline')
        self.assertFalse(result['promoted'])


if __name__ == '__main__':
    unittest.main()
