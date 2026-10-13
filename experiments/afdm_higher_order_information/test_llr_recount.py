import itertools
import unittest
import numpy as np

from experiments.afdm_higher_order_information import llr_recount as r


class RecountContracts(unittest.TestCase):
    def test_dense_proposal_density_and_identity_correction(self):
        nodes=np.array([[0,0],[.2+.3j,-.7+.1j]])
        np.testing.assert_allclose(r.independent_log_ratio(nodes,np.zeros(2),np.eye(2),.5),0,atol=1e-14)
        mean=np.array([.2+.1j,-.1]);cov=np.diag([.7,1.4])
        actual=r.independent_log_ratio(nodes,mean,cov,.5)
        pi=np.exp(-np.sum(abs(nodes)**2,axis=1))/np.pi**2
        q=np.exp(-np.sum(abs(nodes-mean)**2/np.diag(cov),axis=1))/(np.pi**2*np.prod(np.diag(cov)))
        np.testing.assert_allclose(actual,np.log(pi/(.5*pi+.5*q)),atol=1e-14)
        with self.assertRaises(ValueError): r.independent_log_ratio(nodes,mean,np.diag([0.,1.]),.5)
        with self.assertRaises(ValueError): r.independent_log_ratio(nodes,np.array([np.nan,0]),cov,.5)

    def test_complete_population_and_duplicate_rejection(self):
        cases=[dict(case=i,observation=str(i//4)) for i in range(48)]
        messages=[dict(case=c,arm=a,budget=b,replicate=k) for c,a,b,k in itertools.product(
            range(48),r.STUDY_CONFIG['arms'],r.STUDY_CONFIG['budgets'],range(4))]
        r.validate_population(cases,messages)
        with self.assertRaises(ValueError): r.validate_population(cases,messages[:-1])
        messages[-1]=messages[0]
        with self.assertRaises(ValueError): r.validate_population(cases,messages)

    def test_reference_sensitive_classification(self):
        self.assertEqual(r.classification({'a':dict(precision_pass=True),'b':dict(precision_pass=False)}),'reference_sensitive')
        self.assertEqual(r.classification({'a':dict(precision_pass=False)}),'stable_fail')
        self.assertEqual(r.classification({'a':dict(precision_pass=True)}),'stable_pass')


if __name__=='__main__': unittest.main()
