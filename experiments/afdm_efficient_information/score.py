"""Score compression, finite-moment information and frozen score regressions.

All empirical information values are estimates of population objects. Training
orthogonality is never promoted to a population nuisance-orthogonality claim.
"""
import numpy as np


def matrix_pinv(matrix, rcond=1e-10):
    matrix=np.asarray(matrix,float)
    if matrix.ndim!=2 or matrix.shape[0]!=matrix.shape[1] or not np.isfinite(matrix).all():
        raise ValueError('finite square real matrix required')
    matrix=(matrix+matrix.T)/2
    values,vectors=np.linalg.eigh(matrix)
    scale=max(float(values[-1]),1e-30)
    if values[0]<-rcond*scale:
        raise ValueError('moment Gram is not positive semidefinite')
    keep=values>rcond*scale
    inverse=(vectors[:,keep]/values[keep]) @ vectors[:,keep].T
    return inverse,dict(rank=int(keep.sum()),dimension=len(values),eigenvalues=values.tolist(),rcond=rcond)


def efficient_from_fisher(fisher,rcond=1e-10):
    """First coordinate of interest; remaining coordinates are nuisance."""
    fisher=np.asarray(fisher,float)
    if fisher.ndim!=2 or fisher.shape[0]!=fisher.shape[1] or len(fisher)<2 or not np.isfinite(fisher).all():
        raise ValueError('finite Fisher matrix with target and nuisance required')
    inverse,rank=matrix_pinv(fisher[1:,1:],rcond)
    beta=inverse @ fisher[1:,0]
    value=float(fisher[0,0]-fisher[0,1:] @ beta)
    tolerance=rcond*max(1.,abs(float(fisher[0,0])))
    if value < -tolerance:
        raise FloatingPointError('negative Schur residual beyond roundoff')
    return dict(raw=float(fisher[0,0]),effective=max(0.,value),beta=beta,
        nuisance_rank=rank['rank'],fisher=fisher,
        numerical_zero_correction=float(-value) if value<0 else 0.)


def score_information(scores,weights=None):
    scores=np.asarray(scores,float)
    if scores.ndim!=2 or len(scores)==0 or not np.isfinite(scores).all():
        raise ValueError('finite score rows required')
    w=np.full(len(scores),1/len(scores)) if weights is None else np.asarray(weights,float)
    if w.shape!=(len(scores),) or np.any(w<0) or not np.isclose(w.sum(),1.,atol=1e-12):
        raise ValueError('normalized nonnegative row weights required')
    info=efficient_from_fisher((scores.T*w) @ scores)
    info.update(score_mean=w @ scores,residual=scores[:,0]-scores[:,1:] @ info['beta'])
    return info


def conditional_scores(scores,labels,weights=None):
    """Exact conditional expectation on a finite observed partition."""
    scores=np.asarray(scores,float); labels=np.asarray(labels)
    if labels.shape!=(len(scores),):
        raise ValueError('one observed partition label per state required')
    w=np.full(len(scores),1/len(scores)) if weights is None else np.asarray(weights,float)
    if scores.ndim!=2 or not np.isfinite(scores).all() or w.shape!=(len(scores),) or np.any(w<=0) or not np.isclose(w.sum(),1.):
        raise ValueError('finite scores with positive normalized finite-state weights required')
    values,inverse=np.unique(labels,return_inverse=True)
    mass=np.array([w[inverse==j].sum() for j in range(len(values))])
    mean=np.array([(w[inverse==j,None]*scores[inverse==j]).sum(axis=0)/mass[j] for j in range(len(values))])
    return mean,mass,mean[inverse]


def linear_information(features,scores,rcond=1e-10):
    """Plug-in estimate of the nuisance-adjusted linear moment bound.

The evaluation scores may be oracle diagnostics; they do not train or alter the
deployed feature mapping. This is not exact Fisher information of Phi(Y).
"""
    f=np.asarray(features,float); s=np.asarray(scores,float)
    if f.ndim!=2 or s.ndim!=2 or len(f)!=len(s) or len(f)<2 or not np.isfinite(f).all() or not np.isfinite(s).all():
        raise ValueError('matching finite feature and score rows required')
    centered=f-f.mean(axis=0)
    scale=np.sqrt(np.mean(centered**2,axis=0))
    active=scale>1e-14*max(float(scale.max()),1.)
    normalized=centered[:,active]/scale[active]
    covariance=normalized.T @ normalized/len(f)
    inverse,support=matrix_pinv(covariance,rcond) if len(covariance) else (np.empty((0,0)),dict(rank=0,dimension=0,eigenvalues=[],rcond=rcond))
    jacobian=normalized.T @ s/len(f)
    fisher=jacobian.T @ inverse @ jacobian
    result=efficient_from_fisher(fisher,rcond)
    weight=inverse @ (jacobian[:,0]-jacobian[:,1:] @ result['beta'])
    result.update(feature_rank=support['rank'],feature_dimension=f.shape[1],active_features=int(active.sum()),
        covariance=covariance,jacobian=jacobian,nuisance_moment_residual=weight @ jacobian[:,1:],
        feature_weight=weight,active_mask=active,feature_scale=scale,
        interpretation='finite-sample plug-in estimate of population linear moment lower bound')
    return result


class ScoreRegressor:
    """Deterministic standardized ridge regression, frozen before held-out scoring."""
    def __init__(self,ridge):
        if not np.isfinite(ridge) or ridge<0:
            raise ValueError('finite nonnegative ridge required')
        self.ridge=float(ridge)

    def fit(self,features,scores):
        f=np.asarray(features,float); s=np.asarray(scores,float)
        if f.ndim!=2 or s.ndim!=2 or len(f)!=len(s) or len(f)<2 or not np.isfinite(f).all() or not np.isfinite(s).all():
            raise ValueError('matching finite training arrays required')
        self.mean=f.mean(axis=0); self.scale=np.std(f,axis=0)
        self.active=self.scale>1e-14*max(float(self.scale.max()),1.)
        x=(f[:,self.active]-self.mean[self.active])/self.scale[self.active]
        self.score_mean=s.mean(axis=0); self.score_scale=s.std(axis=0)
        self.score_scale=np.where(self.score_scale>1e-14,self.score_scale,1.)
        target=(s-self.score_mean)/self.score_scale
        u,values,vh=np.linalg.svd(x/np.sqrt(len(x)),full_matrices=False)
        keep=values>1e-10*max(float(values[0]) if len(values) else 0.,1e-30)
        multiplier=values[keep]/(values[keep]**2+self.ridge)
        self.coefficients=(vh[keep].T*multiplier) @ (u[:,keep].T @ target/np.sqrt(len(x)))
        self.rank=int(keep.sum()); self.singular_values=values
        return self

    def predict(self,features):
        f=np.asarray(features,float)
        if f.ndim!=2 or f.shape[1]!=len(self.mean) or not np.isfinite(f).all():
            raise ValueError('finite observation features matching frozen regression required')
        return ((f[:,self.active]-self.mean[self.active])/self.scale[self.active] @ self.coefficients)*self.score_scale+self.score_mean

    def state(self):
        return dict(mean=self.mean,scale=self.scale,active=self.active,score_mean=self.score_mean,
            score_scale=self.score_scale,coefficients=self.coefficients,singular_values=self.singular_values,
            ridge=np.array(self.ridge),rank=np.array(self.rank))


def select_regressor(train_features,train_scores,validation_features,validation_scores,ridges):
    fits=[]
    for ridge in ridges:
        model=ScoreRegressor(ridge).fit(train_features,train_scores)
        prediction=model.predict(validation_features)
        loss=float(np.mean(((prediction-validation_scores)/model.score_scale)**2))
        fits.append((loss,ridge,model))
    if not fits:
        raise ValueError('nonempty preregistered ridge grid required')
    best=min(fits,key=lambda x:(x[0],x[1]))
    return best[2],[dict(ridge=r,validation_standardized_mse=v,rank=m.rank) for v,r,m in fits]
