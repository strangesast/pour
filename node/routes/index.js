var express = require('express');
var passport = require('passport');
var router = express.Router();
var Account = require('../models/account');

/* GET home page. */
router.get('/', function(req, res, next) {
  return res.format({
    'html': function() {
      return res.render('index');
    },
    'json': function() {
      return res.json({
        'type': 'text',
        'value': 'Welcome to Pour'
      });
    },
    'default': function() {
      return res.status(406).send('unacceptable request format');
    }
  });
});

router.use('/hash/*', function(req, res, next) {
  var newHash = req.originalUrl.split('hash/').slice(1)[0];
  req.hash_id = newHash;
  return next();
});

router.all('/hash/pour', function(req, res, next) {
  if(req.user || req.query.anonymous) {
    return res.render('pour', function(err, html) {
      return res.json({
        html: html,
        hash_id: req.hash_id
      });
    });
  } else {
    return res.redirect('/hash/account/login');
  }
});

router.get('/hash/account/login', function(req, res, next) {
  var newHash = req.originalUrl.split('hash/').slice(1)[0];
  Account.find({}).then(function(accounts) {
    return res.render('login', {'users' : accounts }, function(err, html) {
      return res.json({
        html : html,
        hash_id: req.hash_id
      });
    });
  });
});
router.post('/hash/account/login', passport.authenticate('local', {
  failureFlash: true,
  failureRedirect: '/hash/account/login'
}), function(req, res) {
  var defaultRedirect = '/hash/account/';
  return res.redirect(req.query.ref || defaultRedirect);
});



router.all('/hash/:hashId', function(req, res, next) {
  return res.json({
    params: req.params,
    hash_id: req.hash_id
  });
});

module.exports = router;
